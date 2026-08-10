import XCTest

final class ProductToCartUITests: XCTestCase {
    private var app: XCUIApplication!

    override func setUpWithError() throws {
        continueAfterFailure = false
        app = XCUIApplication()
        app.launch()
    }

    func testTCMobileCart001ProductCanBeAddedToCart() throws {
        let product = app.staticTexts["Product Name"].firstMatch
        XCTAssertTrue(product.waitForExistence(timeout: 10))
        product.tap()

        let details = app.otherElements["ProductDetails-screen"]
        XCTAssertTrue(details.staticTexts["Sauce Labs Backpack - Black"].waitForExistence(timeout: 10))
        details.buttons["Add To Cart"].tap()
        app.buttons["Cart-tab-item"].tap()

        let cart = app.otherElements["Cart-screen"]
        XCTAssertTrue(cart.staticTexts["Sauce Labs Backpack - Black"].waitForExistence(timeout: 10))
    }
}
