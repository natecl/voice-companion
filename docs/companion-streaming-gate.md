# Frozen persistent-chat provider gate

September 26, 2026. Before live execution: use at most six paid calls (five GPT-6 Luna answers and one Jev retrieval judgment), at the existing conservative $0.01 reservation each. Canonical total before this gate is $2.28/$2.40; read it again before execution. No automatic retry; preserve a failed sequence and diagnose before another version. No new STT calls.

Exercise the actual persistent-chat socket handler, canonical context constructor, storage and unchanged Luna SDK transport:

1. Ask during a synthetic live capture that says Maya enjoys swimming. Answer must mention swimming, cite the live source, and be saved.
2. Finalize with additional speech, then ask “Does that hobby need a pool?” The answer must use the prior conversational subject without a recap; inspect the actual text and saved history.
3. Add an explicit canonical correction to tennis using a synthetic stored transition. Ask what Maya enjoys now. Tennis and the correction citation must take precedence over the older swimming snapshot. This tests read/answer behavior, not extraction model quality.
4. In an empty user's library, answer 2+2 without invented personal evidence or citations.
5. For a different user, anonymous recorded “I am an endurance runner” must not identify the account owner. The answer must retain uncertainty and cite the recording.

Local real-socket replay first covers duplicate IDs with changed attachments/memory/live input, owner isolation, disconnect cleanup, deletion/revocation during streaming, unknown citations, durable completion and explicit memory opt-out. An answer is marked saved only after storage completion. Hosted routes remain disabled; rollout and native QA are separate.

OpenAI [conversation-state guidance](https://developers.openai.com/api/docs/guides/conversation-state) supports explicitly supplying bounded prior context. We keep our own source-aware history and `store=False`, rather than provider-hosted conversation state that could retain deleted derivatives. Existing GPT-6 Luna model/settings and no-automatic-retry transport remain unchanged. No claim is made about hidden reasoning continuity; the existing answer configuration uses reasoning none.
