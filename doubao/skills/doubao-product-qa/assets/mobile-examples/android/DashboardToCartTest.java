package com.saucelabs.mydemoapp.android.view.activities;

import static androidx.test.espresso.Espresso.onView;
import static androidx.test.espresso.action.ViewActions.click;
import static androidx.test.espresso.assertion.ViewAssertions.matches;
import static androidx.test.espresso.matcher.ViewMatchers.isDisplayed;
import static androidx.test.espresso.matcher.ViewMatchers.withId;
import static androidx.test.espresso.matcher.ViewMatchers.withText;

import androidx.test.espresso.contrib.RecyclerViewActions;
import androidx.test.ext.junit.rules.ActivityScenarioRule;
import androidx.test.ext.junit.runners.AndroidJUnit4;
import androidx.test.filters.LargeTest;

import com.saucelabs.mydemoapp.android.R;
import com.saucelabs.mydemoapp.android.actions.NestingAwareScrollAction;
import org.junit.Rule;
import org.junit.Test;
import org.junit.runner.RunWith;

@LargeTest
@RunWith(AndroidJUnit4.class)
public class DashboardToCartTest {
    @Rule
    public ActivityScenarioRule<SplashActivity> activityRule = new ActivityScenarioRule<>(SplashActivity.class);

    @Test
    public void tcMobileCart001ProductCanBeAddedToCart() {
        onView(withId(R.id.productRV)).check(matches(isDisplayed()));
        onView(withId(R.id.productRV)).perform(RecyclerViewActions.actionOnItemAtPosition(0, click()));
        onView(withId(R.id.productTV)).check(matches(withText("Sauce Labs Backpack")));
        onView(withId(R.id.cartBt)).perform(new NestingAwareScrollAction(), click());
        onView(withId(R.id.cartRL)).perform(click());
        onView(withText("Sauce Labs Backpack")).check(matches(isDisplayed()));
    }
}
