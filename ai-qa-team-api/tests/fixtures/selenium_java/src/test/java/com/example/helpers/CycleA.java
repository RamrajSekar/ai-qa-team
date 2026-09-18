package com.example.helpers;

import com.example.helpers.CycleB;

public class CycleA {
    public static void first() { CycleB.second(); }
}
