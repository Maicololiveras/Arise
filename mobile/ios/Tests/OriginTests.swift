import XCTest
@testable import ARISECompanion

final class OriginTests: XCTestCase {
    func testRejectsUnsafeOrigins() {
        for text in ["http://pc.tail.ts.net", "https://evil.com", "https://pc.ts.net.evil.com", "https://user@pc.ts.net", "https://pc.ts.net:443", "https://pc.ts.net/path", "https://pc.ts.net?q=1", "https://pc.ts.net#token", "file:///tmp/a"] {
            XCTAssertNil(Origin(text), text)
        }
    }
    func testAllowsOnlySelectedServer() {
        let origin = Origin("https://pc.tail.ts.net/")!
        XCTAssertTrue(origin.allows(URL(string: "https://pc.tail.ts.net/api/chat")))
        XCTAssertFalse(origin.allows(URL(string: "https://other.tail.ts.net/")))
        XCTAssertFalse(origin.allows(URL(string: "https://pc.tail.ts.net:444/")))
        XCTAssertFalse(origin.allows(URL(string: "http://pc.tail.ts.net/")))
        XCTAssertFalse(origin.allows(URL(string: "https://user@pc.tail.ts.net/")))
    }
}
