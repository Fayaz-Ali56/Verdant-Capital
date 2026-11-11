# 4-minute demo script (rehearse 3 times)

Every number below comes from the bundled evidence or a fresh run. Say "synthetic"
out loud whenever a challenge number appears; judges will probe.

**0:00 Hook.** "Greenwashing is a rare event: under 1% of disclosures. A model that
approves everything is 99% accurate and completely useless. We built for that problem."

**0:25 Boardroom.** Fictional mode, $100,000, moderate risk, strict ESG. Click
*Review this mandate*. Point to three roles: ESG evidence, market signal, constrained allocation.

**1:00 The conflict.** Open the decision room. Fictional FOSS has a bullish market
signal but a high ESG risk. Show the policy resolve it, with cash as the fallback.
Export the audit JSON: "every call has a paper trail."

**1:50 C02, rare events.** Risk Lab, C02/C06. "99:1 split, five seeds, PR-AUC 0.958,
no collapse. At a 1% audit budget, 90% of flags are real: 90x better than random."
Show one false positive and one miss honestly.

**2:25 C06, explainability.** Show a SHAP plot: "A regulator asks why. Here are the
features that drove this flag."

**2:45 C04, the guard.** Risk Lab, C04/C15. "Negative sunlight, a 200% offset,
latitude 95, a NaN from a broken sensor: the bare model returns a confident number
for all of them. Ours rejects or flags every one. 6 injected, 0 confident wrong."

**3:15 C13 + C15, the money.** Decision economics: change the missed-loss cost, show
the threshold move. Then C15: "At 1,000,000 cases, assumed PKR costs, net gain is
PKR 27.27 billion: PKR 27.44bn averted minus PKR 168m of false alarms." Add: "assumptions, not realized savings."

**3:45 Close.** "Make every investment decision smarter, more transparent, more sustainable."

## Likely judge questions
- *Is the data real?* No. Challenge benchmarks are synthetic and labeled. Prices are real cached market data.
- *Why Isolation Forest?* Labels for fraud are scarce; it trains without them.
- *Where do the PKR costs come from?* Illustrative inputs; the form lets you change them.
- *What is not built?* Auth, live execution, real-issuer validation (see docs/LIMITATIONS.md).
