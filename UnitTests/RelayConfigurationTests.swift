import XCTest

final class RelayConfigurationTests: XCTestCase {
    private let token = String(repeating: "a", count: 43)

    func testHostedRequiresPublicTLSAndRejectsCredentialBearingURLs() throws {
        let valid = RelayConfiguration(url: URL(string: "wss://example.com/stt")!, token: token, rootCertificate: nil)
        XCTAssertNoThrow(try valid.validateHosted())
        let session = try valid.makeSession()
        XCTAssertNil(session.delegate) // Use the OS trust store, not a development trust override.
        session.invalidateAndCancel()
        for address in ["ws://example.com/stt", "https://example.com/stt", "wss://example.com/other",
                        "wss://user:secret@example.com/stt", "wss://example.com/stt?token=x", "wss://example.com/stt#x"] {
            XCTAssertThrowsError(try RelayConfiguration(url: URL(string: address)!, token: token, rootCertificate: nil).validateHosted())
        }
        XCTAssertThrowsError(try RelayConfiguration(url: valid.url, token: "short", rootCertificate: nil).validateHosted())
        XCTAssertThrowsError(try RelayConfiguration(url: valid.url, token: token, rootCertificate: "custom-anchor").validateHosted())
    }

    func testProvisioningRemovesTransferOnlyAfterStorageSucceeds() throws {
        let file = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        defer { try? FileManager.default.removeItem(at: file) }
        let config = RelayConfiguration(url: URL(string: "wss://example.com/stt")!, token: token, rootCertificate: nil)
        try JSONEncoder().encode(config).write(to: file)
        XCTAssertThrowsError(try RelayConfiguration.importHosted(from: file) { _ in throw CaptureFailure.noRelay })
        XCTAssertTrue(FileManager.default.fileExists(atPath: file.path))
        var saved: RelayConfiguration?
        _ = try RelayConfiguration.importHosted(from: file) { saved = $0 }
        XCTAssertEqual(saved?.token, token)
        XCTAssertFalse(FileManager.default.fileExists(atPath: file.path))
    }
}
