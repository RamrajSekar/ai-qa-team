package com.example.helpers;

public class TestHelper {
    public static void prepare(String code) { CycleA.first(); }
    public static void overloaded(String value) {}
    public static void overloaded(Object value) {}
}
