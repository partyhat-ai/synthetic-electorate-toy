# Vocabulary

- **Election:** one presidential year (1789–2024), with its certified state results.
- **Slice:** one group of adults in an election (e.g. women in the old suffrage states),
  drawn as a row of dots: who voted for whom, who stayed home, who couldn't vote.
- **Barred:** adults who couldn't legally vote, kept as agents with a reason code. Their vote is never simulated.
- **What-if:** a typed counterfactual change of one kind: *franchise* (who can vote),
  *population* (who lives where), *issue* (what people care about) or *candidate* (who is on the ballot).
- **Rerun:** an election recomputed under one or more what-ifs. An unchanged rerun reproduces history.
- **Backbone:** the calibrated statistical model that decides the counts and reproduces
  certified returns in every draw.
- **Agent / interview:** a synthetic voter answering in both worlds. It supplies only paired,
  within-person changes and quotes, never counts.
- **Bundle:** the per-year JSON the server publishes and the page reads.
- **Profile:** one election's year-specific facts: candidates, blinded descriptors, ballot wording, sources.
- **Narrator:** the robot whose bubble explains a rerun step by step.

Avoid: "prediction" (the page reproduces, then reruns), "AI voters" (they're agents with a stated
role), "accuracy" for R1 (it is enforced by construction, so it isn't validation).
