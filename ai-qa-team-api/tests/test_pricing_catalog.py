"""Display-only pricing catalogue. No database, provider or payment calls."""
import os
import unittest
from copy import deepcopy
from unittest.mock import patch
from pydantic import ValidationError

ENV = {"MONGO_URI":"mongodb://localhost:27017", "MONGO_DB":"pricing_tests", "REDIS_HOST":"localhost",
       "REDIS_PORT":"6379", "REDIS_USERNAME":"test", "REDIS_PASSWORD":"fixture-only",
       "SESSION_SECRET_KEY":"fixture-only", "JWT_SECRET_KEY":"fixture-only"}
with patch.dict(os.environ, ENV):
    from app.config import settings, Settings, PricingSettings, AIAllowanceSettings
    from app.services.ai_allowances import public_pricing, initialize_allowances
    from app.app_config.plan_limits import PLAN_LIMITS


class PricingCatalogTests(unittest.TestCase):
    def setUp(self):
        for name, value in (("pricing", PricingSettings()), ("ai_allowances", AIAllowanceSettings(free_managed=50,free_byok=50))):
            context=patch.object(settings,name,value);context.start();self.addCleanup(context.stop)

    def test_v2_offers_preserve_free_and_disable_purchases(self):
        catalog=public_pricing()
        self.assertEqual(catalog['catalog_version'],2)
        self.assertFalse(catalog['billing_enabled'])
        self.assertEqual(catalog['offers']['free'],{'monthly_usd':0,'availability':'available','users_limit':3,
            'projects_limit':1,'stories_limit':5,'scenarios_limit':10,'testcases_limit':10,
            'managed_ai_credits_limit':50,'byok_ai_requests_limit':50})
        self.assertEqual(catalog['offers']['team']['monthly_usd'],49)
        self.assertEqual(catalog['offers']['business']['testcases_limit'],15000)
        self.assertEqual(catalog['offers']['enterprise'],{'monthly_usd':None,'availability':'planned'})
        self.assertIsNone(catalog['contact_url'])
        self.assertEqual(catalog['add_ons']['managed_pack'],{'requests':500,'usd':10})

    def test_planned_offers_do_not_mutate_live_entitlements_or_legacy_catalogue(self):
        before=deepcopy(PLAN_LIMITS)
        subscription={'plan':'pro','usage':{'managed_ai_credits_used':13}}
        initialize_allowances(subscription)
        stored=deepcopy(subscription)
        settings.pricing.team.managed_ai_credits_limit=1234
        result=public_pricing()
        self.assertEqual(result['offers']['team']['managed_ai_credits_limit'],1234)
        self.assertEqual(result['managed']['managed_ai_credits_limit'],settings.ai_allowances.pro_managed)
        self.assertEqual(result['managed']['monthly_usd'],499)
        self.assertEqual(subscription,stored)
        self.assertEqual(PLAN_LIMITS,before)
        self.assertNotIn('business',PLAN_LIMITS)

    def test_nested_environment_overrides_keep_other_offer_defaults(self):
        with patch.dict(os.environ,{**ENV,'PRICING__TEAM__MONTHLY_USD':'59','PRICING__BUSINESS__USERS_LIMIT':'20',
                                     'PRICING__ADDITIONAL_USER_MONTHLY_USD':'9'}):
            config=Settings(_env_file=None)
        self.assertEqual(config.pricing.team.monthly_usd,59)
        self.assertEqual(config.pricing.team.testcases_limit,3000)
        self.assertEqual(config.pricing.business.users_limit,20)
        self.assertEqual(config.pricing.business.monthly_usd,149)
        self.assertEqual(config.pricing.additional_user_monthly_usd,9)

    def test_contact_is_https_only_and_prices_are_nonnegative(self):
        for url in ('javascript:alert(1)','http://example.com','https://user:fixture@example.com'):
            with self.assertRaises(ValidationError):PricingSettings(contact_url=url)
        with self.assertRaises(ValidationError):PricingSettings(team={'monthly_usd':-1})
        with self.assertRaises(ValidationError):PricingSettings(ai_pack_requests=0)
        settings.pricing.contact_url=PricingSettings(contact_url='https://example.com/contact').contact_url
        self.assertEqual(public_pricing()['contact_url'],'https://example.com/contact')
