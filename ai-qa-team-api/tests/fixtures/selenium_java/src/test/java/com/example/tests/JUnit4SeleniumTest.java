package com.example.tests;

import org.junit.Assert;
import org.junit.Test;
import org.openqa.selenium.WebDriver;
import com.example.helpers.TestHelper;
import com.example.pages.LoginPage;
import com.example.pages.PageAction;

public class JUnit4SeleniumTest {
    private WebDriver driver;
    private LoginPage loginPage;
    private PageAction action;

    @Test
    public void legacyFlow() {
        String code = "variable";
        String contact = createContact();
        loginPage.login("literal", code, System.getenv("TEST_USER"), data.getCode());
        loginPage.navigate("/home");
        driver.get(Config.TEST_URL);
        TestHelper.prepare(code);
        TestHelper.overloaded(code);
        Assert.assertTrue(loginPage.ready());
        action.perform();
        localHelper();
        unknownMethod();
        TestHelper.prepare(contact);
        if (flag) { code = "A"; } else { code = "B"; }
        TestHelper.prepare(code);
    }

    private void localHelper() {
        recursiveHelper();
    }

    private void recursiveHelper() {
        recursiveHelper();
    }
}
