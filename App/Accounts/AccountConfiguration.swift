import Foundation

struct AccountConfiguration {
    static var deletionEnabled: Bool { Bundle.main.object(forInfoDictionaryKey: "EllisAccountDeletionEnabled") as? Bool ?? false }
    let transport: AccountTransport
    let googleClientID: String
    let googleServerClientID: String

    init(bundle: Bundle = .main) throws {
        guard let address = bundle.object(forInfoDictionaryKey: "EllisAccountEndpoint") as? String,
              let endpoint = URL(string: address),
              let client = bundle.object(forInfoDictionaryKey: "GIDClientID") as? String, !client.isEmpty,
              let server = bundle.object(forInfoDictionaryKey: "GIDServerClientID") as? String, !server.isEmpty else {
            throw AccountFailure.unavailable
        }
        transport = try AccountTransport(endpoint: endpoint)
        googleClientID = client
        googleServerClientID = server
    }
}
