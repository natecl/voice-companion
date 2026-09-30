# Independent main-chat state

> Historical native-state checkpoint. Its “not yet connected” status predates the delivered main chat; source-button and deletion descriptions must be read with subsequent release presentation and retained-memory contracts. See [current state](current-state.md) for selected behavior and current evidence boundaries.

September 26, 2026. `CompanionController` owns the main chat, draft, attachment, memory preference and streaming operation independently of recording selection. It is not yet connected to the app interface or hosted rollout.

A submitted request freezes its original question/context. The user can compose a follow-up while it streams. After a saved acknowledgment, a read-only history request obtains durable source locations and current answer validity. If that read fails, the confirmed saved answer remains visible with an error; it is not generated again. An uncertain request can be recovered only by explicit user action, using its original ID and context, never the newly edited draft. Ordinary refresh makes no inference calls. Backgrounding cancels the answer operation; foreground refresh reconciles server state. No local chat cache or new cross-device identity mechanism is introduced.

Every normal connection checks the configured memory owner before network access. An explicitly supplied live capture must belong to that owner. Server authorization remains authoritative. History refresh replaces visible turns with freshly validated server results; older pages are loaded explicitly. Deleted answers therefore cannot be resurrected from an independent native chat cache. Source navigation and attachment synchronization eligibility belong to the following interface checkpoint.

## QA

Run `CoreTests/CompanionConnectionTests` and `CoreTests/CompanionControllerTests` under the Mac scheme with the backend Python configured as described in companion-native-transport.md. Seven focused tests passed. The real Swift controller sent a question through the actual local CompanionService and SQLite store, received its durable turn, preserved a draft edited during generation, and restored identical turn IDs in a new controller. The synthetic provider calls no external API. Targeted failure tests proved explicit recovery preserves the original request, a failed read after confirmed save does not generate again, and invalid input/foreign-owner capture does not reach the network. The shared source also builds for the Phone simulator.

This verifies state and transport, not navigation, physical background behavior or hosted deployment. Those gates remain pending.
