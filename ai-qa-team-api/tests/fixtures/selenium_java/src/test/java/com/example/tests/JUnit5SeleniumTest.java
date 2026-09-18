package com.example.tests;

import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.Test;
import org.openqa.selenium.WebDriver;
import com.example.pages.LoginPage;

public class JUnit5SeleniumTest {
    private WebDriver driver;

    @Test
    void modernFlow() {
        LoginPage page = new LoginPage();
        page.login("literal", "code", System.getenv("TEST_USER"), factory.create());
        driver.get("/modern");
        Assertions.assertEquals("ready", status());
    }
}
