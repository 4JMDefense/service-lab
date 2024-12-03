/* UPDATE THESE VALUES TO MATCH YOUR SETUP */

const STATS_API_URL = "http://ec2-44-229-192-171.us-west-2.compute.amazonaws.com:8100/stats"; // Replace with your VM's IP
const EVENTS_URL = {
    tasks: "http://ec2-44-229-192-171.us-west-2.compute.amazonaws.com:8110/event1", // Replace with the correct endpoint for "tasks"
    completedTasks: "http://ec2-44-229-192-171.us-west-2.compute.amazonaws.com:8110/event2" // Replace with the correct endpoint for "completed tasks"
};

// Fetch and update general statistics
const getStats = (statsUrl) => {
    fetch(statsUrl) // Removed mode: 'no-cors'
        .then(res => {
            if (!res.ok) {
                throw new Error(`Error: status code ${res.status}`);
            }
            return res.json();
        })
        .then((result) => {
            console.log("Received stats", result);
            updateStatsHTML(result);
        }).catch((error) => {
            updateStatsHTML(error.message, true);
        });
};

// Fetch a single event from the audit service
const getEvent = (eventType) => {
    const eventIndex = Math.floor(Math.random() * 101);

    fetch(`${EVENTS_URL[eventType]}?index=${eventIndex}`) // Removed mode: 'no-cors'
        .then(res => {
            if (!res.ok) {
                throw new Error(`Error: status code ${res.status}`);
            }
            return res.json();
        })
        .then((result) => {
            console.log(`Received ${eventType} event`, result);
            updateEventHTML({ ...result, index: eventIndex }, eventType);
        }).catch((error) => {
            updateEventHTML({ error: error.message, index: eventIndex }, eventType, true);
        });
};

// Update a single "event box"
const updateEventHTML = (data, eventType, error = false) => {
    const { index, ...values } = data;
    const elem = document.getElementById(`event-${eventType}`); // Corrected element ID

    elem.innerHTML = `<h5>Event ${index}</h5>`;
    
    if (error) {
        const errorMsg = document.createElement("code");
        errorMsg.innerHTML = values.error;
        elem.appendChild(errorMsg);
        return;
    }

    // Convert object values to a readable format before appending
    Object.entries(values).forEach(([key, value]) => {
        const pElm = document.createElement("p");
        // Check if the value is an object, then convert it to a string
        pElm.innerHTML = `<strong>${key}:</strong> ${typeof value === 'object' ? JSON.stringify(value) : value}`;
        elem.appendChild(pElm);
    });
};

// Update the main statistics div
const updateStatsHTML = (data, error = false) => {
    const elem = document.getElementById("stats");
    elem.innerHTML = error ? `<code>${data}</code>` : "";
    if (!error) {
        Object.entries(data).forEach(([key, value]) => {
            const pElm = document.createElement("p");
            pElm.innerHTML = `<strong>${key}:</strong> ${value}`;
            elem.appendChild(pElm);
        });
    }
};

const setup = () => {
    setInterval(() => {
        getStats(STATS_API_URL);
        getEvent("tasks");
        getEvent("completedTasks");
    }, 5000); // Update every 5 seconds

    // Initial calls
    getStats(STATS_API_URL);
    getEvent("tasks");
    getEvent("completedTasks");
};

document.addEventListener('DOMContentLoaded', setup);

