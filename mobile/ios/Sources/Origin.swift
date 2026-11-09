import Foundation

struct Origin: Equatable {
    let url: URL
    init?(_ value: String) {
        guard let parts = URLComponents(string: value.trimmingCharacters(in: .whitespacesAndNewlines)),
              parts.scheme == "https", let host = parts.host,
              host.hasSuffix(".ts.net"), host.count > 7,
              host.range(of: "^[a-zA-Z0-9.-]+$", options: .regularExpression) != nil,
              parts.port == nil, parts.user == nil, parts.password == nil,
              parts.query == nil, parts.fragment == nil,
              parts.path.isEmpty || parts.path == "/",
              let result = URL(string: "https://" + host.lowercased()) else { return nil }
        url = result
    }
    func allows(_ candidate: URL?) -> Bool {
        guard let candidate else { return false }
        return candidate.scheme == "https" && candidate.host?.lowercased() == url.host &&
            candidate.port == nil && candidate.user == nil && candidate.password == nil
    }
}
