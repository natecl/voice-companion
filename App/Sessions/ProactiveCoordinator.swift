import Foundation
import Observation

/// Foreground capture only. Dictation and ordinary chat never initiate this stream.
@MainActor @Observable
final class ProactiveCoordinator {
    private(set) var isQuiet = false
    private(set) var unavailable = false
    private(set) var latestMessageID: String?
    private var capture: String?
    private var source: MemorySource?
    private var revision = 0
    private var generation = 0
    private var ready = false
    private var waitingForFresh = false
    private var sent: MemorySource?
    private var connection: (any ProactiveConnection)?
    private var task: Task<Void, Never>?
    private var sending: Task<Void, Never>?
    private let makeConnection: () -> any ProactiveConnection
    private let received: () -> Void
    init(makeConnection: @escaping () -> any ProactiveConnection, received: @escaping () -> Void) {
        self.makeConnection = makeConnection; self.received = received
    }

    func update(_ value: MemorySource?, foreground: Bool) {
        guard let value else { suspend(); capture = nil; source = nil; return }
        if value.session_id != capture {
            suspend(); capture = value.session_id; source = nil; sent = nil; revision = 0
            isQuiet = false; unavailable = false; waitingForFresh = false
        }
        let changed = source?.passages != value.passages
        if changed {
            revision += 1
            source = value; source?.revision = revision
        }
        guard foreground else { suspend(); return }
        if waitingForFresh && !changed { return }
        waitingForFresh = false
        guard !isQuiet, !unavailable, let source, !source.passages.isEmpty else { return }
        if task == nil {
            let socket = makeConnection(); connection = socket
            let lease = generation
            task = Task {
                do {
                    try await socket.run(capture: value.session_id) { event in
                        guard self.generation == lease else { return }
                        switch event.type {
                        case "ready":
                            if self.isQuiet { self.quiet() }
                            else {
                                self.ready = event.enabled == true
                                self.isQuiet = event.enabled == false
                                self.flush()
                            }
                        case "quiet": self.isQuiet = true
                        case "contribution":
                            guard !self.isQuiet else { return }
                            self.latestMessageID = event.turn_id
                            self.received()
                        case "unavailable": self.unavailable = true
                        default: break
                        }
                    }
                } catch {
                    if self.generation == lease && !Task.isCancelled { self.unavailable = true }
                }
                if self.generation == lease { self.task = nil; self.ready = false }
            }
        } else { flush() }
    }

    private func flush() {
        guard ready, !isQuiet, !unavailable, sending == nil, let socket = connection else { return }
        let lease = generation
        sending = Task {
            defer { if self.generation == lease { self.sending = nil } }
            do {
                while self.generation == lease, self.ready, !self.isQuiet,
                      let next = self.source, next != self.sent {
                    try Task.checkCancellation()
                    try await socket.observe(next)
                    self.sent = next
                }
            } catch {
                if self.generation == lease && !Task.isCancelled { self.unavailable = true }
            }
        }
    }

    func quiet() {
        isQuiet = true
        guard let capture, let socket = connection else { return }
        // Cancel locally immediately; delivery validation also invalidates at the server.
        ready = false; sending?.cancel(); sending = nil
        Task { try? await socket.quiet(capture: capture) }
    }
    func markRead() { latestMessageID = nil }
    func suspend() {
        generation += 1; ready = false; waitingForFresh = true
        connection?.cancel(); connection = nil
        task?.cancel(); task = nil; sending?.cancel(); sending = nil
        // Reconnect repeats the cutoff for server synchronization, never paid retry.
        sent = nil
    }
}
