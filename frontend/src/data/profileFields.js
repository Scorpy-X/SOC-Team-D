export const profileFields = [
  {
    section: "personal_context",
    name: "life_stage",
    label: "Life stage",
    hint: "Where is the client in their working and personal journey?",
    options: [
      { value: "early_career", label: "Early career" },
      { value: "mid_career", label: "Mid-career" },
      { value: "established_career", label: "Established career" },
      { value: "approaching_retirement", label: "Approaching retirement" },
      { value: "retired", label: "Retired" }
    ]
  },
  {
    section: "personal_context",
    name: "employment_status",
    label: "Employment status",
    hint: "What best describes the client's current work situation?",
    options: [
      { value: "full_time_employed", label: "Full-time employed" },
      { value: "self_employed", label: "Self-employed" },
      { value: "part_time_employed", label: "Part-time employed" },
      { value: "business_owner", label: "Business owner" },
      { value: "retired", label: "Retired" }
    ]
  },
  {
    section: "financial_profile",
    name: "monthly_income_band",
    label: "Monthly income band",
    hint: "How much income comes in each month?",
    options: [
      { value: "under_100000", label: "Under JMD 100,000" },
      { value: "100000_200000", label: "JMD 100,000 to 200,000" },
      { value: "200000_350000", label: "JMD 200,000 to 350,000" },
      { value: "350000_500000", label: "JMD 350,000 to 500,000" },
      { value: "over_500000", label: "Over JMD 500,000" }
    ]
  },
  {
    section: "financial_profile",
    name: "monthly_expenses_band",
    label: "Monthly expenses band",
    hint: "How much is typically spent each month?",
    options: [
      { value: "under_50000", label: "Under JMD 50,000" },
      { value: "50000_100000", label: "JMD 50,000 to 100,000" },
      { value: "100000_200000", label: "JMD 100,000 to 200,000" },
      { value: "200000_350000", label: "JMD 200,000 to 350,000" },
      { value: "over_350000", label: "Over JMD 350,000" }
    ]
  },
  {
    section: "financial_profile",
    name: "savings_band",
    label: "Savings band",
    hint: "Roughly how much has the client already saved?",
    options: [
      { value: "under_100000", label: "Under JMD 100,000" },
      { value: "100000_500000", label: "JMD 100,000 to 500,000" },
      { value: "500000_1000000", label: "JMD 500,000 to 1,000,000" },
      { value: "1000000_3000000", label: "JMD 1,000,000 to 3,000,000" },
      { value: "over_3000000", label: "Over JMD 3,000,000" }
    ]
  },
  {
    section: "investment_profile",
    name: "primary_goal",
    label: "Primary goal",
    hint: "What matters most for this investment?",
    options: [
      { value: "preserve_capital", label: "Preserve capital" },
      { value: "earn_income", label: "Earn income" },
      { value: "save_for_major_goal", label: "Save for a major goal" },
      { value: "retirement", label: "Retirement planning" },
      { value: "grow_wealth", label: "Grow wealth" }
    ]
  },
  {
    section: "investment_profile",
    name: "time_horizon",
    label: "Time horizon",
    hint: "How long can the money stay invested?",
    options: [
      { value: "less_than_1_year", label: "Less than 1 year" },
      { value: "1_to_3_years", label: "1 to 3 years" },
      { value: "3_to_5_years", label: "3 to 5 years" },
      { value: "5_plus_years", label: "5+ years" }
    ]
  },
  {
    section: "investment_profile",
    name: "liquidity_need",
    label: "Liquidity need",
    hint: "How likely is the client to need access to the money soon?",
    options: [
      { value: "very_likely", label: "Very likely" },
      { value: "somewhat_likely", label: "Somewhat likely" },
      { value: "unlikely", label: "Unlikely" }
    ]
  },
  {
    section: "risk_profile_inputs",
    name: "loss_comfort",
    label: "Loss comfort",
    hint: "How comfortable is the client with short-term losses?",
    options: [
      { value: "not_comfortable", label: "Not comfortable" },
      { value: "somewhat_comfortable", label: "Somewhat comfortable" },
      { value: "comfortable", label: "Comfortable" },
      { value: "very_comfortable", label: "Very comfortable" }
    ]
  },
  {
    section: "risk_profile_inputs",
    name: "investment_experience",
    label: "Investment experience",
    hint: "How much investing experience does the client already have?",
    options: [
      { value: "none", label: "None" },
      { value: "limited", label: "Limited" },
      { value: "moderate", label: "Moderate" },
      { value: "strong", label: "Strong" }
    ]
  }
];

const fieldIndex = profileFields.reduce((index, field) => {
  index[field.name] = field;
  return index;
}, {});

export function createEmptyProfileValues() {
  return profileFields.reduce((values, field) => {
    values[field.name] = "";
    return values;
  }, {});
}

export function flattenProfileValues(profile) {
  const values = createEmptyProfileValues();

  if (!profile || typeof profile !== "object") {
    return values;
  }

  profileFields.forEach((field) => {
    values[field.name] = profile[field.section]?.[field.name] ?? "";
  });

  return values;
}

export function buildProfilePayload(flatValues) {
  return profileFields.reduce((payload, field) => {
    if (!payload[field.section]) {
      payload[field.section] = {};
    }

    payload[field.section][field.name] = flatValues[field.name] ?? "";
    return payload;
  }, {});
}

export const allowedProfileValues = profileFields.reduce((values, field) => {
  values[field.name] = field.options.map((option) => option.value);
  return values;
}, {});

export function getFieldByName(fieldName) {
  const field = fieldIndex[fieldName];

  if (!field) {
    throw new Error(`Unknown profile field: ${fieldName}`);
  }

  return field;
}

export function getOptionLabel(fieldName, value) {
  if (!value) {
    return "Not provided";
  }

  const field = fieldIndex[fieldName];
  const option = field?.options.find((item) => item.value === value);

  if (option) {
    return option.label;
  }

  return humanizeValue(value);
}

function humanizeValue(value) {
  return String(value)
    .replace(/_/g, " ")
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}
