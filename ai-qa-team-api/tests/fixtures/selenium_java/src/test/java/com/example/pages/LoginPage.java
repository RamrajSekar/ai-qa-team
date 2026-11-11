package com.example.pages;

import org.openqa.selenium.WebElement;

public class LoginPage extends BasePage {
    private WebElement username;
    private WebElement submit;

    public void login(String literal, String code, String user, String generated) {
        username.sendKeys(user);
        submit.click();
    }

    public boolean ready() {
        return submit.isDisplayed();
    }
}
