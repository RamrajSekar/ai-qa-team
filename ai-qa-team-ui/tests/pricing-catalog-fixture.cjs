// Synthetic display-only catalogue shared by public/workspace browser checks.
module.exports=()=>({catalog_version:2,stage:'EXPERIMENTAL',currency:'USD',billing_enabled:false,contact_url:null,
 offers:{
  free:{monthly_usd:0,availability:'available',users_limit:3,projects_limit:1,stories_limit:5,scenarios_limit:10,testcases_limit:10,managed_ai_credits_limit:50,byok_ai_requests_limit:50},
  team:{monthly_usd:49,availability:'planned',users_limit:5,projects_limit:5,stories_limit:200,scenarios_limit:1000,testcases_limit:3000,managed_ai_credits_limit:500,byok_ai_requests_limit:500},
  business:{monthly_usd:149,availability:'planned',users_limit:15,projects_limit:20,stories_limit:1000,scenarios_limit:5000,testcases_limit:15000,managed_ai_credits_limit:2000,byok_ai_requests_limit:2000},
  enterprise:{monthly_usd:null,availability:'planned'}},
 add_ons:{availability:'planned',additional_user_monthly_usd:8,managed_pack:{requests:500,usd:10},byok_pack:{requests:500,usd:5}}});
