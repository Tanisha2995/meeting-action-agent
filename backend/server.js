import path from "node:path";
import { fileURLToPath } from "node:url";
import express from "express";
import cors from "cors";
import dotenv from "dotenv";

import { extractMeetingActions } from "./ai.js";
import { recommendTeamMembers } from "./recommendation.js";

const currentFile = fileURLToPath(import.meta.url);
const currentDirectory = path.dirname(currentFile);

dotenv.config({
  path: path.resolve(currentDirectory, "../.env")
});
const app = express();

app.use(cors());
app.use(express.json({ limit: "2mb" }));

// 1. Health check
app.get("/", (req, res) => {
  res.json({
    message: "Meeting Action Agent API is running!",
    status: "active"
  });
});

// 2. Analyze meeting transcript and recommend task owners
app.post("/api/analyze", async (req, res) => {
  try {
    const { transcript } = req.body;

    if (!transcript || typeof transcript !== "string") {
      return res.status(400).json({
        success: false,
        message: "Please provide a valid meeting transcript."
      });
    }

    console.log("Analyzing meeting transcript...");

    const result = await extractMeetingActions(transcript);

    // Generate recommendations for tasks without an assigned owner
    const tasksWithRecommendations = await Promise.all(
      result.tasks.map(async (task) => {
        if (task.assignee) {
          return {
            ...task,
            recommended_members: []
          };
        }

        const recommendations = await recommendTeamMembers(
          task.required_skills || []
        );

        return {
          ...task,
          recommended_members: recommendations
        };
      })
    );

    console.log("Meeting analysis completed!");

    return res.status(200).json({
      success: true,
      message: "Meeting analyzed successfully!",
      data: {
        ...result,
        tasks: tasksWithRecommendations
      }
    });

  } catch (error) {
    console.error("Analysis error:", error.message);

    return res.status(500).json({
      success: false,
      message: "Failed to analyze meeting.",
      error: error.message
    });
  }
});

// 3. Get recommendations for a specific task
app.post("/api/recommend", async (req, res) => {
  try {
    const { required_skills } = req.body;

    if (!Array.isArray(required_skills)) {
      return res.status(400).json({
        success: false,
        message: "Please provide required_skills as an array."
      });
    }

    const recommendations =
      await recommendTeamMembers(required_skills);

    return res.status(200).json({
      success: true,
      message: "Recommendations generated successfully!",
      data: recommendations
    });

  } catch (error) {
    console.error("Recommendation error:", error.message);

    return res.status(500).json({
      success: false,
      message: "Failed to generate recommendations.",
      error: error.message
    });
  }
});

// 4. Start server
const PORT = process.env.PORT || 5000;

app.listen(PORT, () => {
  console.log(`Meeting Action Agent running on port ${PORT}`);
});
