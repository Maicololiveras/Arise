import UIKit
import WebKit

final class CompanionController: UIViewController, WKNavigationDelegate, WKUIDelegate {
    private let address = UITextField()
    private let status = UILabel()
    private let container = UIView()
    private var web: WKWebView?
    private var origin: Origin?
    private var generation = 0

    override func viewDidLoad() {
        super.viewDidLoad()
        title = "ARISE Companion"
        view.backgroundColor = .systemBackground
        address.placeholder = "https://your-computer.your-tailnet.ts.net"
        address.borderStyle = .roundedRect
        address.keyboardType = .URL
        address.autocorrectionType = .no
        address.autocapitalizationType = .none
        address.accessibilityLabel = "Private ARISE server address"
        let connect = UIButton(type: .system)
        connect.setTitle("Connect", for: .normal)
        connect.addTarget(self, action: #selector(openConnection), for: .touchUpInside)
        let disconnect = UIButton(type: .system)
        disconnect.setTitle("Disconnect", for: .normal)
        disconnect.addTarget(self, action: #selector(disconnect), for: .touchUpInside)
        let buttons = UIStackView(arrangedSubviews: [connect, disconnect])
        buttons.distribution = .fillEqually
        status.numberOfLines = 0
        status.font = .preferredFont(forTextStyle: .footnote)
        status.adjustsFontForContentSizeCategory = true
        status.text = "Connect Tailscale, then enter the private HTTPS address shown in ARISE on your PC. Pair the chat with its one-use code and authenticator."
        let stack = UIStackView(arrangedSubviews: [address, buttons, status, container])
        stack.axis = .vertical
        stack.spacing = 12
        stack.translatesAutoresizingMaskIntoConstraints = false
        view.addSubview(stack)
        NSLayoutConstraint.activate([
            stack.topAnchor.constraint(equalTo: view.safeAreaLayoutGuide.topAnchor, constant: 12),
            stack.leadingAnchor.constraint(equalTo: view.safeAreaLayoutGuide.leadingAnchor, constant: 16),
            stack.trailingAnchor.constraint(equalTo: view.safeAreaLayoutGuide.trailingAnchor, constant: -16),
            stack.bottomAnchor.constraint(equalTo: view.safeAreaLayoutGuide.bottomAnchor),
            address.heightAnchor.constraint(greaterThanOrEqualToConstant: 44),
            buttons.heightAnchor.constraint(greaterThanOrEqualToConstant: 44)
        ])
    }
    @objc private func openConnection() {
        guard let selected = Origin(address.text ?? "") else {
            status.text = "Use the exact HTTPS .ts.net address, without a path, port or credentials."
            return
        }
        disconnect()
        view.endEditing(true)
        origin = selected
        let epoch = generation
        // Block foreign subresources as well as foreign top-level navigation.
        let escaped = NSRegularExpression.escapedPattern(for: selected.url.host!)
        let rules: [[String: Any]] = [
            ["trigger": ["url-filter": ".*"], "action": ["type": "block"]],
            ["trigger": ["url-filter": "^https://" + escaped + "(/|$)"], "action": ["type": "ignore-previous-rules"]],
            ["trigger": ["url-filter": "^blob:https://" + escaped + "/"], "action": ["type": "ignore-previous-rules"]],
            ["trigger": ["url-filter": "^data:image/(png|jpeg);base64,", "resource-type": ["image"]], "action": ["type": "ignore-previous-rules"]]
        ]
        guard let data = try? JSONSerialization.data(withJSONObject: rules), let json = String(data: data, encoding: .utf8) else { return }
        WKContentRuleListStore.default().compileContentRuleList(forIdentifier: "ARISEPrivateOrigin", encodedContentRuleList: json) { [weak self] rule, error in
            guard let self, self.generation == epoch, self.origin == selected else { return }
            guard let rule, error == nil else { self.status.text = "Could not apply private-connection protection."; return }
            let config = WKWebViewConfiguration()
            // No native JavaScript bridge or shared persistent credentials.
            config.websiteDataStore = .nonPersistent()
            config.userContentController.add(rule)
            config.mediaTypesRequiringUserActionForPlayback = .all
            let web = WKWebView(frame: .zero, configuration: config)
            web.navigationDelegate = self
            web.uiDelegate = self
            web.translatesAutoresizingMaskIntoConstraints = false
            self.container.addSubview(web)
            NSLayoutConstraint.activate([
                web.topAnchor.constraint(equalTo: self.container.topAnchor),
                web.bottomAnchor.constraint(equalTo: self.container.bottomAnchor),
                web.leadingAnchor.constraint(equalTo: self.container.leadingAnchor),
                web.trailingAnchor.constraint(equalTo: self.container.trailingAnchor)
            ])
            self.web = web
            self.status.text = "Connected view. Use the chat's Stop button to stop PC work; Disconnect only closes this device's session."
            web.load(URLRequest(url: selected.url))
        }
    }
    func pauseCapture() {
        web?.setMicrophoneCaptureState(.none, completionHandler: nil)
        web?.pauseAllMediaPlayback(completionHandler: nil)
    }
    @objc private func disconnect() {
        generation += 1
        pauseCapture()
        web?.stopLoading()
        web?.navigationDelegate = nil
        web?.uiDelegate = nil
        web?.removeFromSuperview()
        web = nil
        origin = nil
        status.text = "Disconnected. PC tasks are not cancelled. Use Stop in the paired chat before disconnecting when needed."
    }
    func webView(_ webView: WKWebView, decidePolicyFor action: WKNavigationAction, decisionHandler: @escaping (WKNavigationActionPolicy) -> Void) {
        decisionHandler(origin?.allows(action.request.url) == true && action.targetFrame?.isMainFrame == true ? .allow : .cancel)
    }
    func webView(_ webView: WKWebView, didReceive challenge: URLAuthenticationChallenge, completionHandler: @escaping (URLSession.AuthChallengeDisposition, URLCredential?) -> Void) {
        completionHandler(.performDefaultHandling, nil)
    }
    func webView(_ webView: WKWebView, didFailProvisionalNavigation navigation: WKNavigation!, withError error: Error) {
        status.text = "Connection failed. Check Tailscale, the private HTTPS address and the PC. Certificate errors are never bypassed."
    }
    func webView(_ webView: WKWebView, requestMediaCapturePermissionFor securityOrigin: WKSecurityOrigin, initiatedByFrame frame: WKFrameInfo, type: WKMediaCaptureType, decisionHandler: @escaping (WKPermissionDecision) -> Void) {
        let allowed = type == .microphone && frame.isMainFrame && securityOrigin.protocol == "https" &&
            securityOrigin.host == origin?.url.host && (securityOrigin.port == 0 || securityOrigin.port == 443)
        decisionHandler(allowed ? .prompt : .deny)
    }
}
