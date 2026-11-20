
import OpenAI from "openai";
import dotenv from "dotenv";

// Load environment variables from the project root
dotenv.config({ path: "../.env" });

// Connect to BluesMinds API
const client = new OpenAI({
  apiKey: process.env.BLUESMINDS_API_KEY,
  baseURL: process.env.BLUESMINDS_BASE_URL
});

// Test AI connection
const testAI = async () => {
  try {
    console.log("Connecting to BluesMinds AI...");

    const response = await client.chat.completions.create({
      model: process.env.BLUESMINDS_MODEL,

      messages: [
        {
          role: "system",
          content: `
            You are an AI meeting assistant.
            Extract tasks and decisions from meeting transcripts.
            Return only valid JSON.
            Do not invent missing information.
          `
        },
        {
          role: "user",
          content: `
            Rahul will finish the frontend by November 25.
            The team decided to use Supabase as the database.
          `
        }
      ],

      response_format: {
        type: "json_object"
      }
    });

    console.log("\nAI CONNECTION SUCCESSFUL!");
    console.log("\nMODEL:", response.model);
    console.log("\nAI RESPONSE:");

    const result = JSON.parse(
      response.choices[0].message.content
    );

    console.log(JSON.stringify(result, null, 2));

  } catch (error) {
    console.log("\nAI TEST FAILED!");
    console.log("Error:", error.message);

    if (error.status) {
      console.log("Status:", error.status);
    }
  }
};

// Execute test

