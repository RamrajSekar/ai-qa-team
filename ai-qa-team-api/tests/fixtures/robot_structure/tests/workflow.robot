*** Settings ***
Resource    ../resources/common.resource
Resource    ../resources/duplicate.resource
Resource    ../../../../outside.resource
Resource    ${DYNAMIC_RESOURCE}
Resource    https://example.com/remote.resource

*** Variables ***
${TOUR_CODE}    ABC

*** Test Cases ***
Structural Workflow
    [Tags]    structural    robot
    Local Keyword    literal value    ${VARIABLE_VALUE}
    Unique Resource Keyword    ${TOUR_CODE}
    Duplicate Keyword
    Log    preserved literal
    Unknown Custom Keyword
    ${contact}=    Create Contact
    Local Keyword    ${contact}    ${TOUR_CODE}
    Log    %{TEST_USER}

*** Keywords ***
Local Keyword
    [Arguments]    ${literal}    ${variable}
    Unique Resource Keyword    ${variable}
