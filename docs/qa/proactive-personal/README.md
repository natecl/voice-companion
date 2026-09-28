# Personal proactive contribution evaluation — September 28

Prepared local candidate; no real-model quality claim yet. Founder requested fictional seeding, iterative evaluation and native presentation verification after the saved-video replay produced a relevant but low-value connection. The reset personal account remains empty: all seeding uses isolated temporary databases.

## Evaluation contract

`Backend/fixtures/proactive/personal-cases.json` contains ten explicitly fictional cases: five opportunities (sleep concern, decision constraint, commitment, scheduling preference, unresolved responsibility) and five silence controls (already addressed, wrong person, mere topic connection, unrelated sensitive detail, fictional instructions). Each case declares the expected decision and a human-review rubric before inference. Three unrelated histories are seeded alongside its evidence. All ten retrieved the intended original evidence among three or four candidates.

Run `PYTHONPATH=Backend:scripts/evaluations python3 scripts/evaluations/proactive_personal_cases.py /tmp/proactive-personal-requests.json` to seed, retrieve and export matched baseline/candidate requests. This command makes no model calls. Existing source ownership, identity and correction rules remain unchanged. These cases exercise retrieval from named recorded histories; they do not establish automatic memory extraction quality, broad semantic recall or voice identity.

`Backend/prompts/proactive-v2-candidate.md` prioritizes a missing detail that changes an immediate action/question/decision, rather than thematic connections or recaps. It asks for concise reminders, minimal private disclosure and conservative identity attribution. It is deliberately not wired as the production prompt until real-model comparison passes. Expected benefit is a hypothesis.

Planned real-Luna evaluation needs a new allowance: ten baseline calls, ten candidate calls and up to ten targeted refinement/validation calls, with no automatic retries. Inspect usefulness, evidence fidelity, identity, novelty, timing, brevity and appropriate silence. Report failures, not just decision accuracy. Do not deploy the candidate on simulated output alone.

## Native behavior and appearance

Actual iPhone Simulator execution with the local authenticated socket, durable backend and explicitly synthetic recording/model passed `ProactiveUITests/testContributionUsesMainChatPreservesDraftAndQuietDoesNotStopCapture`. It checks message arrival as an ordinary gray chat bubble, normal text, no repeated author heading, horizontal bounds, preserved composer draft, quiet without stopping capture, the new-message scroll affordance, and exactly one saved message after app relaunch. The screenshot was visually inspected: message, recording controls and composer are legible, separated and within the viewport. This is synthetic-provider UI evidence, not a real-model or physical-device quality test. Existing 37 proactive backend tests passed.

![Actual native proactive message](native-message.png)
