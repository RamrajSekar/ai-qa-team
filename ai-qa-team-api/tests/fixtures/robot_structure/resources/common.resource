*** Settings ***
Resource    nested.resource

*** Keywords ***
Unique Resource Keyword
    [Arguments]    ${code}
    Deep Keyword    ${code}
    Log    ${code}

Duplicate Keyword
    Log    common
