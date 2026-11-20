
import { supabase } from "./supabase.js";

export const recommendTeamMembers = async (requiredSkills) => {
  if (!Array.isArray(requiredSkills)) {
    throw new Error("Required skills must be an array.");
  }

  // Fetch team profiles from Supabase
  const { data: teamMembers, error } = await supabase
    .from("users")
    .select("id, name, skill, experience_level");

  if (error) {
    throw new Error("Could not fetch team profiles: " + error.message);
  }

  const normalize = (skill) => skill.toLowerCase().trim();

  const recommendations = teamMembers.map((member) => {
   const memberSkills = Array.isArray(member.skill)
  ? member.skill.map(normalize)
  : (member.skill || "").split(",").map(normalize);
    const matchedSkills = requiredSkills.filter((skill) =>
      memberSkills.includes(normalize(skill))
    );

    const matchPercentage =
      requiredSkills.length === 0
        ? 0
        : Math.round(
            (matchedSkills.length / requiredSkills.length) * 100
          );

    return {
      user_id: member.id,
      name: member.name,
      match_percentage: matchPercentage,
      matched_skills: matchedSkills,
      missing_skills: requiredSkills.filter(
        (skill) => !memberSkills.includes(normalize(skill))
      ),
      recommendation_reason:
        matchedSkills.length > 0
          ? `Matches ${matchedSkills.join(", ")}`
          : "No matching skills found"
    };
  });

  return recommendations
    .filter((member) => member.match_percentage > 0)
    .sort((a, b) => b.match_percentage - a.match_percentage)
    .slice(0, 3);
};
