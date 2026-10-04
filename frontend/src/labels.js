// Plain-language names for the technical values. Wording rule: "potentially unusual", never "fraud".
export const FACTOR = {
  "AmountDeviation:normal": "Amount is normal", "AmountDeviation:high": "Amount is high", "AmountDeviation:very_high": "Amount is very high",
  "NewMerchant:yes": "Merchant is new", "NewMerchant:no": "Merchant is familiar",
  "CategoryOverspend:yes": "Category spending above usual", "CategoryOverspend:no": "Category spending normal",
  "UnusualTime:yes": "Unusual time of day", "UnusualTime:no": "Usual time of day",
};
export const VARIABLE = { AmountDeviation: "Amount deviation", NewMerchant: "New merchant", CategoryOverspend: "Category overspend", UnusualTime: "Unusual time", UnusualTransaction: "Unusual transaction" };
export const factorLabel = (v, s) => FACTOR[v + ":" + s] || v + " = " + s;
export const OUTCOME = {
  logged_routine: "Routine: logged after a quick check", logged_normal: "Looks normal: logged",
  awaiting_user: "Needs your answer", flagged: "Potentially unusual: flagged for your review", logged_user_confirmed: "You confirmed it: logged",
};
export const TOOL = {
  get_transaction_history: "Look up merchant history", get_category_statistics: "Read category statistics",
  check_risk_rules: "Check risk rules", run_bayesian_analysis: "Run Bayesian analysis", predict_month_end: "Predict month-end spend",
  generate_explanation: "Write explanation", ask_user: "Ask the user", log_transaction: "Log transaction", user_answer: "Your answer",
};
export const whyBad = (evidence) => Object.entries(evidence || {}).filter(([, s]) => s !== "normal" && s !== "no").map(([v, s]) => factorLabel(v, s)).join(", ") || "nothing unusual";
