let currentLanguage = 'en';
let chatSessionId = null;
let lastAnalysisResults = null;

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
    const newLanguage = document.getElementById('languageSelect').value;
    if (currentLanguage === newLanguage) return;
    
    currentLanguage = newLanguage;
    localStorage.setItem('preferredLanguage', currentLanguage);
    updateLanguageStrings();

    // Retranslate analysis results if available
    if (lastAnalysisResults) {
        retranslateAnalysisResults(currentLanguage);
    }

    // Update chat language
    updateChatLanguage(currentLanguage);
}

async function retranslateAnalysisResults(language) {
    try {
        // Show progress indicator
        document.getElementById('analysisStatus').style.display = 'block';
        updateProgress(1, 2, translations[currentLanguage]?.translating || 'Translating analysis...');

        const response = await fetch('/retranslate', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                language: language
            })
        });

        if (!response.ok) {
            throw new Error(`Retranslation failed with status ${response.status}`);
        }

        const translatedData = await response.json();
        if (translatedData.status === 'success') {
            lastAnalysisResults = translatedData;
            displayAnalysisResults(translatedData);
            updateProgress(2, 2, translations[currentLanguage]?.translation_complete || 'Translation complete');
            console.log('Retranslated results displayed:', translatedData);
        } else {
            throw new Error(translatedData.error || 'Retranslation failed');
        }
    } catch (error) {
        console.error('Retranslation error:', error);
        showError(`Retranslation error: ${error.message}`);
    } finally {
        document.getElementById('analysisStatus').style.display = 'none';
    }
}

async function updateChatLanguage(language) {
    if (!chatSessionId) return; // No active chat session

    try {
        const response = await fetch('/api/chat/update_language', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                language: language
            })
        });

        if (!response.ok) {
            throw new Error(`Chat language update failed with status ${response.status}`);
        }

        const data = await response.json();
        if (data.status !== 'success') {
            throw new Error(data.error || 'Chat language update failed');
        }
        console.log(`Chat language updated to ${language}`);
    } catch (error) {
        console.error('Chat language update error:', error);
        showError(`Chat language update error: ${error.message}`);
    }
}

function displayResults(data) {
    lastAnalysisResults = data;
    displayAnalysisResults(data);
}

function updateProgress(step, total, message) {
    const progressSection = document.querySelector(".progress-section");
    const progressFill = document.querySelector(".progress-fill");
    const statusMessage = document.getElementById("statusMessage");

    progressSection.style.display = "block";
    const percentage = (step / total) * 100;

    progressFill.style.transition = "width 0.3s ease";
    progressFill.style.width = `${percentage}%`;

    statusMessage.innerHTML = `
        <span class="progress-step">${step}/${total}</span>
        <span class="progress-message">${message}</span>
    `;
}

async function initializeChat(contractText) {
    const chatMessages = document.getElementById('chatMessages');
    if (chatMessages) {
        chatMessages.innerHTML = '';
    }

    const chatInput = document.getElementById('chatInput');
    const sendButton = document.getElementById('sendMessage');
    if (chatInput) chatInput.disabled = true;
    if (sendButton) sendButton.disabled = true;

    await endChatSession();

    if (!contractText) {
        console.log('No contract text provided for chat initialization');
        return;
    }

    try {
        const response = await fetch('/api/chat/start', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                contract_text: contractText,
                language: currentLanguage
            })
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();
        if (data.status === 'success') {
            chatSessionId = data.session_id;
            console.log('Chat session started with ID:', chatSessionId);
            if (chatInput) chatInput.disabled = false;
            if (sendButton) sendButton.disabled = false;
        } else {
            throw new Error(data.error || 'Failed to initialize chat');
        }
    } catch (error) {
        console.error('Chat initialization error:', error);
        showError('Chat initialization failed: ' + error.message);
    }
}

async function sendChatMessage() {
    const chatInput = document.getElementById('chatInput');
    const message = chatInput.value.trim();

    if (!message) return;

    if (!chatSessionId) {
        showError('No active chat session. Please analyze a contract first.');
        return;
    }

    displayChatMessage(message, true);
    chatInput.value = '';

    try {
        const response = await fetch('/api/chat/message', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                message: message,
                language: currentLanguage
            })
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();
        if (data.status === 'success') {
            displayChatMessage(data.response);
        } else {
            throw new Error(data.error || 'Failed to process message');
        }
    } catch (error) {
        console.error('Chat error:', error);
        displayChatMessage(`Error: ${error.message}`);
        if (error.message.includes('No active chat session')) {
            showError('Chat session expired. Please reanalyze the contract.');
            initializeChat();
        }
    }
}

async function endChatSession() {
    if (!chatSessionId) return;

    try {
        const response = await fetch('/api/chat/end', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });

        const data = await response.json();
        if (data.status === 'success') {
            console.log('Chat session ended');
        } else {
            console.warn('Failed to end chat session:', data.error);
        }
    } catch (error) {
        console.error('Error ending chat session:', error);
    } finally {
        chatSessionId = null;
        const chatInput = document.getElementById('chatInput');
        const sendButton = document.getElementById('sendMessage');
        if (chatInput) chatInput.disabled = true;
        if (sendButton) sendButton.disabled = true;
    }
}

async function handleFileUpload(event) {
    event.preventDefault();
    console.log('Starting file upload process...');

    const resultsContainer = document.getElementById('results');
    resultsContainer.style.display = 'none';

    const fileInput = document.getElementById('contractFile');
    const languageSelect = document.getElementById('languageSelect');

    if (!fileInput.files || fileInput.files.length === 0) {
        showError('Please select a file to analyze');
        return;
    }

    const formData = new FormData();
    formData.append('file', fileInput.files[0]);
    formData.append('language', languageSelect.value);

    document.getElementById('analysisStatus').style.display = 'block';
    updateProgress(1, 4, 'Extracting text from document...');

    try {
        console.log('Sending extract request...');
        const extractResponse = await fetch('/api/document/extract', {
            method: 'POST',
            body: formData
        });

        if (!extractResponse.ok) {
            const errorData = await extractResponse.json();
            throw new Error(errorData.error || 'Failed to extract text');
        }

        const extractData = await extractResponse.json();
        console.log('Extracted data:', extractData);

        if (extractData.status !== 'success') {
            throw new Error(extractData.error || 'Text extraction failed');
        }

        updateProgress(2, 4, 'Analyzing contract...');

        console.log('Sending analysis request...');
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

        if (!analyzeResponse.ok) {
            const errorData = await analyzeResponse.json();
            throw new Error(errorData.error || 'Analysis failed');
        }

        const analysisData = await analyzeResponse.json();
        console.log('Analysis data:', analysisData);

        if (analysisData.status === 'success') {
            updateProgress(4, 4, 'Analysis complete');
            displayAnalysisResults(analysisData);
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

function showError(message) {
    const errorDiv = document.getElementById('errorMessage');
    errorDiv.textContent = message;
    errorDiv.style.display = 'block';

    setTimeout(() => {
        errorDiv.style.display = 'none';
    }, 5000);
}

function displayAnalysisResults(data) {
    if (data.status !== 'success') {
        showError('Failed to process analysis results');
        return;
    }

    console.log('Displaying analysis results:', data);
    lastAnalysisResults = data;

    localStorage.setItem('analysisData', JSON.stringify({
        contract_text: data.document_text,
        shadow_analysis: data.shadow_analysis,
        summary_analysis: data.summary
    }));

    initializeChat(data.document_text);

    document.getElementById('summaryContent').innerHTML = `
        <div class="summary-section">
            <h3 data-lang-key="contract_text">Contract Text</h3>
            <pre class="contract-text">${data.document_text.replace(/\n/g, '<br>')}</pre>
        </div>
    `;

    displayContractSummary(data.summary?.summary || {});
    displayScoresGrid(data.summary?.structured_analysis || {});
    displayShadowAnalysis({ content: data.shadow_analysis });
    updateScoreBadges(data.evaluation || {});
    updateLanguageStrings(); // Ensure labels are updated

    document.getElementById('results').style.display = 'block';
}

function displayContractSummary(summary) {
    console.log('Displaying contract summary:', summary);

    // Handle cases where summary fields are undefined or not strings
    const keyPoints = typeof summary.key_points === 'string' && summary.key_points.trim()
        ? summary.key_points.split('\n').filter(p => p.trim())
        : [];
    const potentialIssues = typeof summary.potential_issues === 'string' && summary.potential_issues.trim()
        ? summary.potential_issues.split('\n').filter(p => p.trim())
        : [];
    const recommendations = typeof summary.recommendations === 'string' && summary.recommendations.trim()
        ? summary.recommendations.split('\n').filter(p => p.trim())
        : [];

    const summaryContent = document.getElementById('summaryContent');
    summaryContent.innerHTML += `
        <div class="summary-section">
            <h3 data-lang-key="executive_summary">${translations[currentLanguage]?.executive_summary || 'Executive Summary'}</h3>
            <p>${summary.executive_summary || translations[currentLanguage]?.no_summary || 'No summary available'}</p>
            <div class="summary-details">
                <h4 data-lang-key="key_points">${translations[currentLanguage]?.key_points || 'Key Points'}</h4>
                <ul class="data-list">
                    ${keyPoints.length > 0 ? keyPoints.map(point => `<li>${point}</li>`).join('') : `<li>${translations[currentLanguage]?.no_key_points || 'No key points available'}</li>`}
                </ul>
                <h4 data-lang-key="potential_issues">${translations[currentLanguage]?.potential_issues || 'Potential Issues'}</h4>
                <ul class="data-list">
                    ${potentialIssues.length > 0 ? potentialIssues.map(issue => `<li>${issue}</li>`).join('') : `<li>${translations[currentLanguage]?.no_issues || 'No issues identified'}</li>`}
                </ul>
                <h4 data-lang-key="recommendations">${translations[currentLanguage]?.recommendations || 'Recommendations'}</h4>
                <ul class="data-list">
                    ${recommendations.length > 0 ? recommendations.map(rec => `<li>${rec}</li>`).join('') : `<li>${translations[currentLanguage]?.no_recommendations || 'No recommendations provided'}</li>`}
                </ul>
            </div>
        </div>
    `;
}

function displayScoresGrid(analysis) {
    const scoresHtml = Object.entries(analysis)
        .filter(([key]) => key !== 'overall_score')
        .map(([key, value]) => `
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
        `)
        .join('');

    document.getElementById('scoresGrid').innerHTML = scoresHtml;
}

function displayShadowAnalysis(shadowData) {
    const shadowContent = document.getElementById('shadowContent');
    shadowContent.innerHTML = `
        <div class="shadow-section">
            <div class="shadow-text">
                ${formatShadowContent(shadowData.content)}
            </div>
        </div>
    `;
}

function formatShadowContent(content) {
    if (!content) return '<p>No analysis available</p>';
    return content
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/^### (.*)$/gm, '<h3>$1</h3>')
        .replace(/^#### (.*)$/gm, '<h4>$1</h4>')
        .replace(/^\* (.*)$/gm, '<li>$1</li>')
        .replace(/\n\n/g, '</p><p>')
        .replace(/\n/g, '<br>')
        .replace(/<p>\s*<li>/g, '<ul><li>')
        .replace(/<\/li>\s*<li>/g, '</li><li>')
        .replace(/<\/li>\s*<\/p>/g, '</li></ul></p>')
        .trim();
}

function updateScoreBadges(evaluation) {
    const overallScore = evaluation.evaluation?.overall_score * 10 || 0;
    document.getElementById('summaryScore').innerHTML = `
        <div class="score-value">${Math.round(overallScore)}%</div>
        <div class="score-label" data-lang-key="overall_score">Overall Score</div>
    `;
    document.getElementById('shadowScore').innerHTML = `
        <div class="score-value">${Math.round(overallScore)}%</div>
        <div class="score-label" data-lang-key="analysis_accuracy">Analysis Accuracy</div>
    `;
}

function getScoreClass(score) {
    if (score <= 3) return "low-score";
    if (score >= 8) return "high-score";
    return "";
}

function formatTitle(key) {
    return key.replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase());
}

function displayChatMessage(message, isUser = false) {
    const chatMessages = document.getElementById("chatMessages");
    const messageDiv = document.createElement("div");
    messageDiv.className = `chat-message ${isUser ? "user-message" : "bot-message"}`;

    const formattedMessage = message
        .split("\n\n")
        .map(para => {
            if (para.includes('\n- ')) {
                const items = para.split('\n- ').filter(item => item.trim());
                const listItems = items.map((item, index) => {
                    const text = index === 0 ? item : item.replace(/^- /, '');
                    return text.trim() ? `<li>${text.trim()}</li>` : '';
                }).join('');
                return `<ul>${listItems}</ul>`;
            }
            return `<p>${para.trim()}</p>`;
        })
        .join("");

    messageDiv.innerHTML = formattedMessage;
    chatMessages.appendChild(messageDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('uploadForm');
    if (form) {
        form.addEventListener('submit', handleFileUpload);
        console.log('Form submit handler attached');
    } else {
        console.error('Upload form not found!');
    }

    const chatInput = document.getElementById('chatInput');
    const sendButton = document.getElementById('sendMessage');

    if (chatInput) {
        chatInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendChatMessage();
            }
        });
    }

    if (sendButton) {
        sendButton.addEventListener('click', sendChatMessage);
    }

    const savedLanguage = localStorage.getItem('preferredLanguage');
    if (savedLanguage) {
        document.getElementById('languageSelect').value = savedLanguage;
        currentLanguage = savedLanguage;
    }
    updateLanguageStrings();
    initializeChat();

    window.addEventListener('beforeunload', endChatSession);
});