package com.example.tests;

import org.openqa.selenium.WebDriver;
import org.testng.Assert;
import org.testng.annotations.Test;

public class TestNgSeleniumTest {
    private WebDriver driver;

    @Test
    public void testNgFlow() {
        driver.quit();
        Assert.assertTrue(true);
    }
}
