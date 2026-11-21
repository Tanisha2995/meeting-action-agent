
const API_BASE = "http://127.0.0.1:8000";

// DOM elements
const analyzeBtn = document.getElementById("analyzeBtn");
const titleInput = document.getElementById("meetingTitle");
const transcriptInput = document.getElementById("transcript");
const message = document.getElementById("analysisMessage");

const resultsPanel = document.getElementById("results");
const summaryText = document.getElementById("summaryText");
const decisionList = document.getElementById("decisionList");
const taskList = document.getElementById("taskList");

// Prevent HTML injection when displaying API data
function escapeHTML(value) {
    return String(value ?? "").replace(/[&<>"']/g, char => ({
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#039;"
    })[char]);
}

// Format dates for display
function formatDate(value) {
    if (!value) return "No deadline specified";

    const date = new Date(value);

    if (Number.isNaN(date.getTime())) return value;

    return date.toLocaleDateString("en-IN", {
        day: "numeric",
        month: "short",
        year: "numeric"
    });
}

// Display meeting analysis
function displayAnalysis(data) {
    const meeting = data.meeting;
    const decisions = data.decisions || [];
    const tasks = data.tasks || [];

    document.getElementById("resultTitle").textContent =
        meeting.title || "Meeting analysis";

    summaryText.textContent =
        meeting.summary || "No summary available.";

    // Decisions
    decisionList.innerHTML = decisions.length
        ? decisions.map(decision => `
            <div class="result-item">
                <h4>${escapeHTML(decision.decision_text)}</h4>
                <p>Evidence: "${escapeHTML(decision.context_quote)}"</p>
            </div>
        `).join("")
        : "<p>No decisions were identified.</p>";

    // Tasks
    taskList.innerHTML = tasks.length
        ? tasks.map(task => `
            <div class="result-item">
                <h4>${escapeHTML(task.title)}</h4>
                <p>${escapeHTML(task.description)}</p>
                <p class="meta">
                    Priority: ${escapeHTML(task.priority || "MEDIUM")}
                    · Deadline: ${escapeHTML(formatDate(task.due_date))}
                </p>
                <p class="meta">
                    Status: ${escapeHTML(task.status || "OPEN")}
                </p>
                <p class="meta">
                    Required skills: ${
                        escapeHTML(
                            Array.isArray(task.required_skills)
                                ? task.required_skills.join(", ")
                                : task.required_skills || "Not specified"
                        )
                    }
                </p>
                <p class="meta">
                    Confidence: ${
                        Math.round((Number(task.confidence_score) || 0) * 100)
                    }%
                </p>
            </div>
        `).join("")
        : "<p>No actionable tasks were identified.</p>";

    resultsPanel.hidden = false;

    resultsPanel.scrollIntoView({
        behavior: "smooth",
        block: "start"
    });
}

// Load dashboard statistics
async function loadDashboard() {
    try {
        const response = await fetch(`${API_BASE}/api/tasks`);

        if (!response.ok) {
            throw new Error("Could not load tasks.");
        }

        const tasks = await response.json();

        const completed = tasks.filter(
            task => task.status === "COMPLETED"
        ).length;

        document.getElementById("totalTasks").textContent = tasks.length;
        document.getElementById("pendingTasks").textContent =
            tasks.length - completed;
        document.getElementById("completedTasks").textContent = completed;

    } catch (error) {
        console.error("Dashboard loading error:", error);
    }
}

// Analyze meeting
analyzeBtn.addEventListener("click", async () => {
    const title = titleInput.value.trim();
    const transcript = transcriptInput.value.trim();

    if (!title || !transcript) {
        message.textContent = "Please enter a meeting title and transcript.";
        return;
    }

    analyzeBtn.disabled = true;
    analyzeBtn.textContent = "✧ Analyzing...";
    message.textContent = "AI is analyzing your meeting. Please wait.";

    try {
        // Send transcript to FastAPI
        const response = await fetch(
            `${API_BASE}/api/meetings/ingest`,
            {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({
                    title: title,
                    transcript: transcript
                })
            }
        );

        const result = await response.json();

        if (!response.ok) {
            throw new Error(
                result.detail || "Meeting analysis failed."
            );
        }

        // Fetch saved meeting, decisions and tasks
        const meetingResponse = await fetch(
            `${API_BASE}/api/meetings/${result.meeting_id}`
        );

        if (!meetingResponse.ok) {
            throw new Error("Meeting saved, but results could not be loaded.");
        }

        const meetingData = await meetingResponse.json();

        displayAnalysis(meetingData);

        message.textContent =
            `Successfully analyzed! ${result.tasks_extracted} tasks extracted.`;

        await loadDashboard();

    } catch (error) {
        console.error("Analysis error:", error);

        message.textContent =
            error.message || "Unable to connect to the backend.";

    } finally {
        analyzeBtn.disabled = false;
        analyzeBtn.textContent = "Analyze with AI →";
    }
});

// Initial dashboard load
loadDashboard();

// Refresh statistics periodically
setInterval(loadDashboard, 15000);
