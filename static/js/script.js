document.addEventListener("DOMContentLoaded", function () {
    // Get references to the DOM elements
    const playlistContainer = document.getElementById("playlist");
    const emotionDisplay = document.getElementById("emotion-display");
    const spotifyLink = document.getElementById("spotify-link");
    const darkModeToggle = document.getElementById("dark-mode-toggle");

    // Check if all required elements are present
    if (!playlistContainer || !emotionDisplay || !spotifyLink || !darkModeToggle) {
        console.error("Missing one or more required HTML elements.");
        return;
    }

    let lastDetectedEmotion = "";

    // Function to fetch the detected emotion from the backend
    async function fetchEmotion() {
        console.log("Fetching detected emotion...");

        try {
            const response = await fetch("/get_emotion");
            if (!response.ok) throw new Error(`HTTP error! Status: ${response.status}`);

            const data = await response.json();
            console.log("Emotion Data Received:", data);

            if (data.emotion && typeof data.emotion === "string") {
                const newEmotion = data.emotion.trim().toLowerCase();

                // Update the UI only if the emotion has changed
                if (newEmotion !== "waiting" && newEmotion !== lastDetectedEmotion) {
                    lastDetectedEmotion = newEmotion;
                    emotionDisplay.textContent = `Detected Emotion: ${data.emotion}`;
                    updatePlaylist(newEmotion);
                } else {
                    console.log(`Emotion '${data.emotion}' has not changed, skipping update.`);
                }
            } else {
                console.warn("No valid emotion detected.");
                emotionDisplay.textContent = "Waiting for emotion detection...";
            }
        } catch (error) {
            console.error("Error fetching emotion:", error);
            emotionDisplay.textContent = "Error detecting emotion.";
        }
    }

    // Function to fetch and display the recommended playlist based on the detected emotion
    async function updatePlaylist(emotion) {
        const lowerEmotion = emotion.toLowerCase();
        console.log(`Fetching playlist for emotion: ${lowerEmotion}`);

        try {
            const response = await fetch(`/recommend?emotion=${lowerEmotion}`);
            if (!response.ok) throw new Error(`HTTP error! Status: ${response.status}`);

            const data = await response.json();
            console.log("🎵 Playlist Data Received:", data);

            // Clear the existing playlist
            playlistContainer.innerHTML = "";

            // Handle server errors
            if (data.error) {
                console.warn(`Server Error: ${data.error}`);
                playlistContainer.innerHTML = `<p class="error-message">${data.error}</p>`;
                spotifyLink.style.display = "none";
                return;
            }

            // Handle case where no tracks are found
            if (!data.tracks || data.tracks.length === 0) {
                console.warn(`No tracks found for emotion: ${lowerEmotion}`);
                playlistContainer.innerHTML = `
                    <p class="no-recommendation">
                        No recommendations available for "${lowerEmotion}". Try changing expressions or refreshing.
                    </p>`;
                spotifyLink.style.display = "none";
                return;
            }

            // Split tracks into two sections: upper (first 5) and lower (next 5)
            const upperTracks = data.tracks.slice(0, 5); // First 5 tracks
            const lowerTracks = data.tracks.slice(5, 10); // Next 5 tracks

            // Create and append the upper section of the playlist
            const upperSection = document.createElement("div");
            upperSection.classList.add("upper-section");
            const upperGrid = document.createElement("div");
            upperGrid.classList.add("playlist-grid");

            upperTracks.forEach(track => {
                const trackElement = document.createElement("div");
                trackElement.classList.add("playlist-item");
                trackElement.innerHTML = `
                    <img src="${track.album_cover || 'default-image.jpg'}" alt="${track.name}">
                    <p>${track.name} - ${track.artist}</p>
                    <a href="${track.spotify_url}" target="_blank" class="spotify-play">▶ Play</a>
                `;
                upperGrid.appendChild(trackElement);
            });

            upperSection.appendChild(upperGrid);
            playlistContainer.appendChild(upperSection);

            // Create and append the lower section of the playlist
            const lowerSection = document.createElement("div");
            lowerSection.classList.add("lower-section");
            const lowerGrid = document.createElement("div");
            lowerGrid.classList.add("playlist-grid");

            lowerTracks.forEach(track => {
                const trackElement = document.createElement("div");
                trackElement.classList.add("playlist-item");
                trackElement.innerHTML = `
                    <img src="${track.album_cover || 'default-image.jpg'}" alt="${track.name}">
                    <p>${track.name} - ${track.artist}</p>
                    <a href="${track.spotify_url}" target="_blank" class="spotify-play">▶ Play</a>
                `;
                lowerGrid.appendChild(trackElement);
            });

            lowerSection.appendChild(lowerGrid);
            playlistContainer.appendChild(lowerSection);

            // Update the Spotify playlist link
            if (data.spotify_playlist_url) {
                spotifyLink.href = data.spotify_playlist_url;
                spotifyLink.style.display = "inline-block";
            } else {
                spotifyLink.style.display = "none";
            }
        } catch (error) {
            console.error("Error fetching playlist:", error);
            playlistContainer.innerHTML = `
                <p class="error-message">Failed to load recommendations. Please try again.</p>
            `;
        }
    }

    // Dark mode toggle functionality
    darkModeToggle.addEventListener("click", function () {
        document.body.classList.toggle("dark-mode");
        const isDarkMode = document.body.classList.contains("dark-mode");
        darkModeToggle.textContent = isDarkMode ? "☀️ Light Mode" : "🌙 Dark Mode";
        console.log(`Dark mode ${isDarkMode ? "enabled" : "disabled"}`);
    });

    // Fetch the detected emotion every 5 seconds
    setInterval(fetchEmotion, 5000);

    // Fetch the emotion immediately on page load
    fetchEmotion();
});