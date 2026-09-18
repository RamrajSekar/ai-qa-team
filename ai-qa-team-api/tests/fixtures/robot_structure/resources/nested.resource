*** Settings ***
Resource    common.resource

*** Keywords ***
Deep Keyword
    [Arguments]    ${value}
    Unique Resource Keyword    ${value}
