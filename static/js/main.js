function updateLanguageStrings() {
        const elements = document.querySelectorAll('[data-lang-key]');
        elements.forEach(element => {
          const key = element.getAttribute('data-lang-key');
          if (translations[currentLanguage]?.[key]) {
            if (element.tagName === 'INPUT' && element.type === 'text') {
              element.placeholder = translations[currentLanguage][key];
            } else {
              element.textContent = translations[currentLanguage][key];
            }
          }
        });
      }

      function changeLanguage() {
        currentLanguage = document.getElementById('languageSelect').value;
        localStorage.setItem('preferredLanguage', currentLanguage);
        updateLanguageStrings();
        
        // Reinitialize chat with new language if chat is active
        if (document.getElementById('results').style.display !== 'none') {
            initializeChat();
        }
      }

      function updateProgress(step, total, message) {
        const progressSection = document.querySelector(".progress-section");
        const progressFill = document.querySelector(".progress-fill");
        const statusMessage = document.getElementById("statusMessage");

        progressSection.style.display = "block";
        const percentage = (step / total) * 100;

        // Animate the progress bar
        progressFill.style.transition = "width 0.3s ease";
        progressFill.style.width = `${percentage}%`;

        // Update status message with progress
        statusMessage.innerHTML = `
                <span class="progress-step">${step}/${total}</span>
                <span class="progress-message">${message}</span>
            `;
      }

      async function handleFileUpload(event) {
        event.preventDefault();
        console.log('Starting file upload process...');
        
        // Clear any previous results immediately
        const resultsContainer = document.getElementById('results');
        resultsContainer.style.display = 'none';
        
        const fileInput = document.getElementById('contractFile');
        const languageSelect = document.getElementById('languageSelect');

        if (!fileInput.files || fileInput.files.length === 0) {
            showError('Please select a file to analyze');
            return;
        }

        // Create FormData and append file and language
        const formData = new FormData();
        formData.append('file', fileInput.files[0]);
        formData.append('language', languageSelect.value);

        // Show loading state
        document.getElementById('analysisStatus').style.display = 'block';
        updateProgress(1, 4, 'Extracting text from document...');

        try {
            console.log('Sending extract request...');
            // First step: Extract text
            const extractResponse = await fetch('/api/document/extract', {
                method: 'POST',
                body: formData
            });

            console.log('Extract response:', extractResponse);

            if (!extractResponse.ok) {
                const errorData = await extractResponse.json();
                throw new Error(errorData.error || 'Failed to extract text');
            }

            const extractData = await extractResponse.json();
            console.log('Extracted data:', extractData);
            
            if (extractData.status !== 'success') {
                throw new Error(extractData.error || 'Text extraction failed');
            }

            // Update progress
            updateProgress(2, 4, 'Analyzing contract...');

            console.log('Sending analysis request...');
            // Second step: Full analysis
            const analyzeResponse = await fetch('/analyze', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json'
                },
                body: JSON.stringify({
                    text: extractData.text,
                    language: languageSelect.value
                })
            });

            console.log('Analysis response:', analyzeResponse);

            if (!analyzeResponse.ok) {
                const errorData = await analyzeResponse.json();
                throw new Error(errorData.error || 'Analysis failed');
            }

            const analysisData = await analyzeResponse.json();
            console.log('Analysis data:', analysisData);
            
            if (analysisData.status === 'success') {
                updateProgress(4, 4, 'Analysis complete');
                displayResults(analysisData);
                resultsContainer.style.display = 'block';
            } else {
                throw new Error(analysisData.error || 'Analysis failed');
            }

        } catch (error) {
            console.error('Error:', error);
            showError(error.message);
            resultsContainer.style.display = 'none';
        } finally {
            document.getElementById('analysisStatus').style.display = 'none';
        }
      }

      async function sendMessage() {
        const chatInput = document.getElementById('chatInput');
        const message = chatInput.value.trim();
        
        if (!message) return;

        // Get stored analysis data
        const analysisData = JSON.parse(localStorage.getItem('analysisData') || '{}');

        // Display user message
        displayChatMessage(message, true);
        chatInput.value = '';

        try {
            const response = await fetch('/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    message: message,
                    language: currentLanguage, // Make sure to send current language
                    contract_text: analysisData.contract_text,
                    shadow_analysis: analysisData.shadow_analysis,
                    summary_analysis: analysisData.summary_analysis
                })
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            
            if (data.status === 'error') {
                const errorMessage = translations[currentLanguage]?.error_message || 'Error occurred';
                throw new Error(errorMessage);
            }

            displayChatMessage(data.response);

        } catch (error) {
            const errorPrefix = translations[currentLanguage]?.error_prefix || 'Error';
            displayChatMessage(`${errorPrefix}: ${error.message}`);
        }
      }

      function showError(message) {
        const errorDiv = document.getElementById('errorMessage');
        errorDiv.textContent = message;
        errorDiv.style.display = 'block';
        
        // Hide error after 5 seconds
        setTimeout(() => {
            errorDiv.style.display = 'none';
        }, 5000);
      }

      function displayResults(data) {
        const resultsContainer = document.getElementById('results');
        
        // Helper function to safely display arrays
        const formatList = (items) => {
            if (!items || !Array.isArray(items)) return 'No items available';
            return items.map(item => `<li>${item}</li>`).join('');
        };

        // Helper function to safely get nested objects
        const safeGet = (obj, path) => {
            return path.split('.').reduce((acc, part) => acc && acc[part], obj) || {};
        };

        // Create the results HTML
        resultsContainer.innerHTML = `
            <div class="analysis-section card">
                <h2>Contract Analysis Results</h2>
                
                <div class="analysis-item">
                    <h3>Summary</h3>
                    <div class="summary-content">
                        <div class="summary-section">
                            <h4>Overview</h4>
                            <p>${safeGet(data, 'summary.overview') || 'No overview available'}</p>
                        </div>
                        
                        <div class="summary-section">
                            <h4>Key Points</h4>
                            <ul>
                                ${formatList(safeGet(data, 'summary.key_points'))}
                            </ul>
                        </div>
                        
                        <div class="summary-section">
                            <h4>Risks</h4>
                            <ul>
                                ${formatList(safeGet(data, 'summary.risks'))}
                            </ul>
                        </div>
                        
                        <div class="summary-section">
                            <h4>Recommendations</h4>
                            <ul>
                                ${formatList(safeGet(data, 'summary.recommendations'))}
                            </ul>
                        </div>
                    </div>
                </div>

                <div class="analysis-item">
                    <h3>Evaluation Scores</h3>
                    <div class="scores-grid">
                        ${Object.entries(safeGet(data, 'evaluation.scores') || {})
                            .map(([key, value]) => `
                                <div class="score-item">
                                    <div class="score-label">${key}</div>
                                    <div class="score-value">${typeof value === 'number' ? value.toFixed(1) : value}</div>
                                </div>
                            `).join('')}
                    </div>
                </div>

                <div class="analysis-item">
                    <h3>Shadow Analysis</h3>
                    <pre class="shadow-content">${JSON.stringify(data.shadow_analysis || {}, null, 2)}</pre>
                </div>
            </div>
        `;

        // Show the results container
        resultsContainer.style.display = 'block';
      }

      function displayContractSummary(summary) {
        document.getElementById("summaryContent").innerHTML = `
                <div class="summary-section">
                    <h3 data-lang-key="executive_summary">Executive Summary</h3>
                    <p>${summary.executive_summary}</p>
                    
                    <div class="summary-details">
                        <h4 data-lang-key="key_points">Key Points</h4>
                        <ul class="data-list">${summary.key_points
                          .map((point) => `<li>${point}</li>`)
                          .join("")}</ul>
                        
                        <h4 data-lang-key="potential_issues">Potential Issues</h4>
                        <ul class="data-list">${summary.potential_issues
                          .map((issue) => `<li>${issue}</li>`)
                          .join("")}</ul>
                        
                        <h4 data-lang-key="recommendations">Recommendations</h4>
                        <ul class="data-list">${summary.recommendations
                          .map((rec) => `<li>${rec}</li>`)
                          .join("")}</ul>
                    </div>
                </div>
            `;
      }

      function displayScoresGrid(analysis) {
        const scoresHtml = Object.entries(analysis)
          .map(
            ([key, value]) => `
                    <div class="score-card ${getScoreClass(value.score)}">
                        <div class="score-header">
                            <h4>${formatTitle(key)}</h4>
                            <div class="score-info">
                                <span class="score-badge">${value.score}/10</span>
                            </div>
                        </div>
                        ${value.content ? `
                            <div class="score-content">
                                <p>${value.content}</p>
                            </div>
                        ` : ''}
                    </div>
                `
          )
          .join("");

        document.getElementById("scoresGrid").innerHTML = scoresHtml;
      }

      function displayShadowAnalysis(shadowData) {
        const shadowContent = document.getElementById('shadowContent');
        
        // Display the shadow analysis content
        shadowContent.innerHTML = `
            <div class="shadow-section">
                <div class="shadow-text">
                    ${formatShadowContent(shadowData.content)}
                </div>
                <div class="model-evaluations">
                    <h4>Model Evaluations</h4>
                    <div class="model-scores">
                        ${Object.entries(shadowData.evaluation.scores)
                            .map(([model, score]) => `
                                <div class="model-score">
                                    <span class="model-name">${model.split('/')[1]}</span>
                                    <span class="score-badge">${score}%</span>
                                </div>
                            `).join('')}
                    </div>
                </div>
            </div>
        `;
      }

      function formatShadowContent(content) {
        // Remove markdown formatting and apply HTML formatting
        return content
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\n\n/g, '</p><p>')
            .replace(/\n/g, '<br>')
            .replace(/•/g, '&#8226;')
            .trim();
      }

      function updateScoreBadges(evaluation) {
        // Update Shadow Analysis score badge
        document.getElementById('shadowScore').innerHTML = `
            <div class="score-value">${Math.round(evaluation.shadow_analysis.evaluation.average)}%</div>
            <div class="score-label" data-lang-key="analysis_accuracy">Analysis Accuracy</div>
        `;

        // Update Summary score badge
        document.getElementById('summaryScore').innerHTML = `
            <div class="score-value">${Math.round(evaluation.summary_evaluation.average)}%</div>
            <div class="score-label" data-lang-key="overall_score">Overall Score</div>
        `;
      }

      function getScoreClass(score) {
        if (score <= 3) return "low-score";
        if (score >= 8) return "high-score";
        return "";
      }

      function formatTitle(key) {
        return key.replace(/_/g, " ").toUpperCase();
      }

      function toggleScoreDetails(element) {
        const details = element.parentElement.querySelector(".score-details");
        const icon = element.querySelector(".mdi");

        if (details.style.maxHeight) {
          details.style.maxHeight = null;
          icon.classList.replace("mdi-chevron-up", "mdi-chevron-down");
        } else {
          details.style.maxHeight = details.scrollHeight + "px";
          icon.classList.replace("mdi-chevron-down", "mdi-chevron-up");
        }
      }

      function displayChatMessage(message, isUser = false) {
        const chatMessages = document.getElementById("chatMessages");
        const messageDiv = document.createElement("div");
        messageDiv.className = `chat-message ${
          isUser ? "user-message" : "bot-message"
        }`;

        // Format message into paragraphs
        const formattedMessage = message
          .split("\n\n")
          .map((para) => `<p>${para.trim()}</p>`)
          .join("");

        messageDiv.innerHTML = formattedMessage;
        chatMessages.appendChild(messageDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;
      }

      function processExtractedText(text) {
        // Show the results container
        const resultsContainer = document.getElementById('results');
        resultsContainer.style.display = 'block';

        // Update summary content
        const summaryContent = document.getElementById('summaryContent');
        summaryContent.innerHTML = `
            <div class="extracted-text">
                <h3>Extracted Text</h3>
                <pre>${text}</pre>
            </div>
        `;

        // Enable the analysis buttons now that we have text
        document.querySelectorAll('.analysis-btn').forEach(btn => {
            btn.disabled = false;
        });

        // Start the analysis pipeline
        analyzeContract(text);
      }

      async function analyzeContract(text) {
        try {
            const language = document.getElementById('languageSelect').value;
            
            // Show analysis status
            const statusElement = document.getElementById('analysisStatus');
            statusElement.style.display = 'block';
            statusElement.textContent = 'Analyzing contract...';

            const response = await fetch('/analyze', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    text: text,
                    language: language
                })
            });

            if (!response.ok) {
                throw new Error('Analysis failed');
            }

            const data = await response.json();
            displayAnalysisResults(data);

        } catch (error) {
            showError('Analysis failed: ' + error.message);
        } finally {
            document.getElementById('analysisStatus').style.display = 'none';
        }
      }

      function displayAnalysisResults(data) {
        if (!data.status === 'success') {
            showError('Failed to process analysis results');
            return;
        }

        // Display Shadow Analysis
        const shadowContent = document.getElementById('shadowContent');
        shadowContent.innerHTML = `
            <div class="analysis-results">
                <pre>${JSON.stringify(data.shadow_analysis, null, 2)}</pre>
            </div>
        `;

        // Display Summary
        const summaryContent = document.getElementById('summaryContent');
        summaryContent.innerHTML = `
            <div class="analysis-results">
                <pre>${JSON.stringify(data.summary, null, 2)}</pre>
            </div>
        `;

        // Display Evaluation Scores
        const scoresGrid = document.getElementById('scoresGrid');
        if (data.evaluation && data.evaluation.scores) {
            scoresGrid.innerHTML = Object.entries(data.evaluation.scores)
                .map(([category, score]) => `
                    <div class="score-item">
                        <div class="score-label">${category}</div>
                        <div class="score-value">${score.toFixed(2)}</div>
                    </div>
                `).join('');
        }

        // Show the results container
        document.getElementById('results').style.display = 'block';
      }

      document.addEventListener('DOMContentLoaded', function() {
        const form = document.getElementById('uploadForm');
        if (form) {
            form.addEventListener('submit', handleFileUpload);
            console.log('Form submit handler attached');
        } else {
            console.error('Upload form not found!');
        }
      });

      document.getElementById('chatInput').addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            e.preventDefault();
            sendMessage();
        }
      });

      document.addEventListener('DOMContentLoaded', () => {
        const savedLanguage = localStorage.getItem('preferredLanguage');
        if (savedLanguage) {
          document.getElementById('languageSelect').value = savedLanguage;
          currentLanguage = savedLanguage;
        }
        updateLanguageStrings();
        initializeChat();
      });