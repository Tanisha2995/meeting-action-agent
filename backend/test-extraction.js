
import { extractMeetingActions } from "./ai.js";

const transcript = `
Meeting: Product Development

Tanisha: We need to build a frontend dashboard for our application.

Rahul: I think we need React and JavaScript for that.

Priya: I will handle the database integration using Supabase.

Aman: We should test the application before the final demo.

Tanisha: Let's complete everything before the hackathon presentation.
`;

const runTest = async () => {
  try {
    console.log("==================================");
    console.log("MEETING ACTION AGENT - AI TEST");
    console.log("==================================");

    console.log("\nAnalyzing meeting transcript...\n");

    const result = await extractMeetingActions(transcript);

    console.log("EXTRACTION SUCCESSFUL!\n");

    console.log("MEETING SUMMARY:");
    console.log(result.summary);

    console.log("\nEXTRACTED TASKS:");

    result.tasks.forEach((task, index) => {
      console.log(`\nTask ${index + 1}:`);
      console.log("Title:", task.title);
      console.log("Description:", task.description);
      console.log("Required Skills:", task.required_skills);
      console.log("Assignee:", task.assignee);
      console.log("Priority:", task.priority);
      console.log("Due Date:", task.due_date);
      console.log("Confidence:", task.confidence_score);
      console.log("Ambiguity:", task.ambiguity_reason);
    });

    console.log("\nEXTRACTED DECISIONS:");
    console.log(JSON.stringify(result.decisions, null, 2));

    console.log("\n==================================");
    console.log("TEST COMPLETED");
    console.log("==================================");

  } catch (error) {
    console.error("\nEXTRACTION FAILED!");
    console.error(error);
  }
};

runTest();
