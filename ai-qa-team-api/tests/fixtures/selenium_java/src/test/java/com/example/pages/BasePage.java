package com.example.pages;

import org.openqa.selenium.WebDriver;

public class BasePage {
    protected WebDriver driver;

    public void navigate(String path) {
        driver.get(path);
    }
}
