import XCTest

final class CompanionMessageTextTests: XCTestCase {
    func testSavedAndRetainedGroundingTagsAreHidden() {
        XCTAssertEqual(CompanionMessageText.display("Maya swims [[p1]]."), "Maya swims.")
        XCTAssertEqual(CompanionMessageText.display("At the garden [[p2]] [[p3]]. Tomorrow [[m1]]."), "At the garden. Tomorrow.")
        XCTAssertEqual(CompanionMessageText.display("First [[p1]]\nSecond [[p2]]"), "First\nSecond")
    }

    func testEveryCitationStreamingBoundaryRemainsInvisible() {
        let text = "Maya swims. [[p123]]"
        for length in "Maya swims.".count...text.count {
            XCTAssertEqual(CompanionMessageText.display(String(text.prefix(length)), streaming: true), "Maya swims.")
        }
        XCTAssertEqual(CompanionMessageText.display(text + " And reads.", streaming: true), "Maya swims. And reads.")
    }

    func testInterruptedAnswerDoesNotExposeUnfinishedTag() {
        XCTAssertEqual(CompanionMessageText.display("Maya swims. [[p12]"), "Maya swims.")
        XCTAssertEqual(CompanionMessageText.display("Maya swims. [[p"), "Maya swims.")
    }

    func testOrdinaryTextAndBracketsArePreserved() {
        XCTAssertEqual(CompanionMessageText.display("Use [Monday] or [Tuesday]."), "Use [Monday] or [Tuesday].")
        XCTAssertEqual(CompanionMessageText.display("Try [[wiki]]."), "Try [[wiki]].")
        XCTAssertEqual(CompanionMessageText.display("A [", streaming: false), "A [")
        XCTAssertEqual(CompanionMessageText.display("No diagnosis was established."), "No diagnosis was established.")
    }
}
