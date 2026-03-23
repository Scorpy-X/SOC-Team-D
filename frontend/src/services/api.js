import { getMockRecommendation } from "./mockApi";

export async function submitInvestorProfile(profile) {
  return getMockRecommendation(profile);
}
