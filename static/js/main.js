// static/js/main.js
let currentLanguage = localStorage.getItem('preferredLanguage') || 'en';
let chatSessionId = null;
let lastAnalysisResults = null;
let searchTimeout = null;

function checkAuth() {
    if (!localStorage.getItem('user_id')) {
        // Only redirect if not already on the login page
        if (window.location.pathname !== '/auth/login') {
            window.location.href = '/auth/login';
        }
        return false;
    }
    return true;
}

function updateLanguageStrings() {
    document.querySelectorAll('[data-lang-key]').forEach(element => {
        const key = element.getAttribute('data-lang-key');
        if (translations[currentLanguage]?.[key]) {
            if (element.tagName === 'TEXTAREA' || (element.tagName === 'INPUT' && element.type === 'text')) {
                element.placeholder = translations[currentLanguage][key];
            } else {
                element.textContent = translations[currentLanguage][key];
            }
        }
    });
}

function updateMarksTranslations() {
    document.querySelectorAll('[data-mark-key]').forEach(element => {
        const key = element.getAttribute('data-mark-key');
        element.textContent = translations[currentLanguage]?.marks?.[key] || formatTitle(key);
    });
}

function changeLanguage() {
    const newLanguage = document.getElementById('languageSelect').value;
    if (currentLanguage === newLanguage) return;

    console.log(`Changing language to ${newLanguage}`);
    currentLanguage = newLanguage;
    localStorage.setItem('preferredLanguage', currentLanguage);

    updateLanguageStrings();
    updateMarksTranslations();

    if (lastAnalysisResults) {
        retranslateAnalysisResults(currentLanguage);
    } else {
        updateChatLanguage(currentLanguage);
    }
}

function disableInputs(disable) {
    const languageSelect = document.getElementById('languageSelect');
    const chatInput = document.getElementById('chatInput');
    const sendButton = document.getElementById('sendMessage');

    if (languageSelect) languageSelect.disabled = disable;
    if (chatInput) chatInput.disabled = disable;
    if (sendButton) sendButton.disabled = disable;
}

async function retranslateAnalysisResults(language) {
    try {
        document.getElementById('analysisStatus').style.display = 'block';
        updateProgress(1, 2, translations[currentLanguage]?.translating || 'Translating...', true);
        disableInputs(true);

        const response = await fetch('/retranslate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ language, user_id: localStorage.getItem('user_id') })
        });

        const data = await response.json();
        if (!response.ok) throw new Error(data.error || 'Retranslation failed');

        if (data.status === 'success') {
            lastAnalysisResults = data;
            displayAnalysisResults(data);
            updateProgress(2, 2, translations[currentLanguage]?.translation_complete || 'Translation complete');
            await restartChat(language);
        } else {
            throw new Error(data.error || 'Retranslation failed');
        }
    } catch (error) {
        showError(`${translations[currentLanguage]?.retranslation_error || 'Translation error'}: ${error.message}`);
        if (lastAnalysisResults) displayAnalysisResults(lastAnalysisResults);
    } finally {
        document.getElementById('analysisStatus').style.display = 'none';
        disableInputs(false);
    }
}

async function restartChat(language) {
    await endChatSession();
    if (lastAnalysisResults?.document_text) {
        await initializeChat(lastAnalysisResults.document_text);
        await updateChatLanguage(language);
    } else {
        showError(translations[currentLanguage]?.no_contract_text || 'No contract text available.');
    }
}

async function updateChatLanguage(language) {
    try {
        const response = await fetch('/api/chat/update_language', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ language, user_id: localStorage.getItem('user_id') })
        });

        const data = await response.json();
        if (data.status !== 'success') throw new Error(data.error || 'Language update failed');
    } catch (error) {
        showError(`${translations[currentLanguage]?.chat_language_error || 'Language error'}: ${error.message}`);
    }
}

async function initializeChat(contractText) {
    const chatMessages = document.getElementById('chatMessages');
    const chatInput = document.getElementById('chatInput');
    const sendButton = document.getElementById('sendMessage');

    if (chatMessages) chatMessages.innerHTML = '';
    if (chatInput) chatInput.disabled = true;
    if (sendButton) sendButton.disabled = true;

    if (!contractText) {
        showError(translations[currentLanguage]?.no_contract_text || 'No contract text.');
        return;
    }

    try {
        const response = await fetch('/api/chat/start', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                contract_text: contractText,
                language: currentLanguage,
                user_id: localStorage.getItem('user_id')
            })
        });

        const data = await response.json();
        if (data.status === 'success') {
            chatSessionId = data.session_id;
            if (chatInput) chatInput.disabled = false;
            if (sendButton) sendButton.disabled = false;
            fetchFrequentQuestions(); // Load questions after chat initialization
        } else {
            throw new Error(data.error || 'Chat initialization failed');
        }
    } catch (error) {
        showError(`${translations[currentLanguage]?.chat_init_error || 'Chat init failed'}: ${error.message}`);
    }
}

async function sendChatMessage() {
    const chatInput = document.getElementById('chatInput');
    const message = chatInput?.value.trim();

    if (!message) {
        showError(translations[currentLanguage]?.error || 'Enter a message.');
        return;
    }

    if (!chatSessionId) {
        showError(translations[currentLanguage]?.no_chat_session || 'No active chat session.');
        return;
    }

    displayChatMessage(message, true);
    chatInput.value = '';
    chatInput.style.height = 'auto';
    document.getElementById('sendMessage').disabled = true;
    chatInput.disabled = true;

    displayTypingIndicator();

    try {
        const response = await fetch('/api/chat/message', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                session_id: chatSessionId,
                message,
                user_id: localStorage.getItem('user_id')
            })
        });

        const data = await response.json();
        if (data.status === 'success') {
            removeTypingIndicator();
            displayChatMessage(data.response);
            fetch('/auth/check')
            .then(res => res.json())
            .then(data => {
                if (data.authenticated) {
                    fetchFrequentQuestions();
            } else {
            window.location.href = '/auth/login';
            }
        });
        } else {
            throw new Error(data.error || 'Message failed');
        }
    } catch (error) {
        removeTypingIndicator();
        showError(`${translations[currentLanguage]?.chat_error || 'Chat error'}: ${error.message}`);
    } finally {
        chatInput.disabled = false;
        document.getElementById('sendMessage').disabled = false;
    }
}

async function endChatSession() {
    if (!chatSessionId) return;

    try {
        const response = await fetch('/api/chat/end', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ session_id: chatSessionId, user_id: localStorage.getItem('user_id') })
        });

        const data = await response.json();
        if (data.status !== 'success') console.warn('Failed to end session:', data.error);
    } catch (error) {
        console.error('Error ending session:', error);
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
    const resultsContainer = document.getElementById('results');
    const fileInput = document.getElementById('contractFile');
    const chatSection = document.getElementById('chatSection');
    const frequentQuestionsSection = document.getElementById('frequentQuestionsSection');

    if (!fileInput.files.length) {
        showError(translations[currentLanguage]?.no_file_selected || 'Select a file.');
        return;
    }

    const formData = new FormData();
    formData.append('file', fileInput.files[0]);
    formData.append('language', currentLanguage);

    const analysisStatus = document.getElementById('analysisStatus');
    analysisStatus.style.display = 'block';
    updateProgress(1, 4, translations[currentLanguage]?.extracting_text || 'Extracting text...', true);

    try {
        const extractResponse = await fetch('/api/document/extract', {
            method: 'POST',
            body: formData
        });

        const extractData = await extractResponse.json();
        if (extractData.status !== 'success') throw new Error(extractData.error || 'Extraction failed');

        updateProgress(2, 4, translations[currentLanguage]?.analyzing_contract || 'Analyzing...', true);

        const analyzeResponse = await fetch('/analyze', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                text: extractData.text,
                language: currentLanguage,
                user_id: localStorage.getItem('user_id')
            })
        });

        const analysisData = await analyzeResponse.json();
        if (analysisData.status !== 'success') throw new Error(analysisData.error || 'Analysis failed');

        lastAnalysisResults = analysisData;
        updateProgress(4, 4, translations[currentLanguage]?.analysis_complete || 'Analysis complete');
        displayAnalysisResults(analysisData);
        await initializeChat(analysisData.document_text);
        if (chatSection) chatSection.style.display = 'block';
        if (frequentQuestionsSection) frequentQuestionsSection.style.display = 'block';
        fetchFrequentQuestions();
        resultsContainer.style.display = 'block';
    } catch (error) {
        showError(`${translations[currentLanguage]?.error_occurred || 'Error'}: ${error.message}`);
        resultsContainer.style.display = 'none';
    } finally {
        analysisStatus.style.display = 'none';
    }
}

async function fetchFrequentQuestions() {
    if (!checkAuth()) return;

    try {
        const response = await fetch('/api/chat/frequent_questions', {
            method: 'GET',
            headers: { 
                'Content-Type': 'application/json',
                'X-User-ID': localStorage.getItem('user_id') || ''
            }
        });

        // Avoid redirecting on 401/403; instead, handle gracefully
        if (response.status === 401 || response.status === 403) {
            console.warn('Authentication check failed, clearing local storage');
            localStorage.removeItem('user_id');
            if (window.location.pathname !== '/auth/login') {
                window.location.href = '/auth/login';
            }
            return;
        }

        const data = await response.json();
        if (data.status === 'success') {
            displayFrequentQuestions(data.questions);
        } else {
            throw new Error(data.error || 'Failed to load frequent questions');
        }
    } catch (error) {
        console.error('Error fetching frequent questions:', error);
        // Display default questions instead of error to avoid breaking UI
        displayFrequentQuestions([
            {"question": "What are the termination clauses?", "response": "What are the termination clauses?", "count": 0},
            {"question": "Is the non-compete clause enforceable?", "response": "Is the non-compete clause enforceable?", "count": 0},
            {"question": "What are the salary details?", "response": "What are the salary details?", "count": 0}
        ]);
    }
}

function displayFrequentQuestions(questions) {
    const container = document.getElementById('frequentQuestions');
    if (!container) return;

    container.innerHTML = questions.length ? questions.map(q => `
        <button class="question-btn" onclick="useSuggestedQuestion('${q.response.replace(/'/g, "\\'")}')">
            ${q.response} (${q.count})
        </button>
    `).join('') : `<p data-lang-key="no_questions">${translations[currentLanguage]?.no_questions || 'No frequent questions.'}</p>`;
}

function useSuggestedQuestion(question) {
    const chatInput = document.getElementById('chatInput');
    if (chatInput) {
        chatInput.value = question;
        chatInput.focus();
    }
}

async function fetchChatHistory() {
    if (!checkAuth()) return;

    try {
        const response = await fetch('/api/chat/history', {
            method: 'GET',
            headers: { 
                'Content-Type': 'application/json',
                'X-User-ID': localStorage.getItem('user_id') || ''
            }
        });

        if (response.status === 401 || response.status === 403) {
            localStorage.removeItem('user_id');
            window.location.href = '/auth/login';
            return;
        }

        const data = await response.json();
        if (data.status === 'success') {
            displayChatHistory(data.history);
        } else {
            showError(translations[currentLanguage]?.history_error || 'Failed to load history');
        }
    } catch (error) {
        showError(translations[currentLanguage]?.history_error || 'Error loading history');
    }
}

function displayChatHistory(history) {
    const container = document.getElementById('chatHistory');
    if (!container) return;

    container.innerHTML = history.length ? history.map(h => `
        <div class="history-item">
            <p><strong data-lang-key="question">${translations[currentLanguage]?.question || 'Question'}:</strong> ${h.question}</p>
            <p><strong data-lang-key="response">${translations[currentLanguage]?.response || 'Response'}:</strong> ${h.response}</p>
            <p><small>${new Date(h.asked_at).toLocaleString()}</small></p>
        </div>
    `).join('') : `<p data-lang-key="no_history">${translations[currentLanguage]?.no_history || 'No chat history.'}</p>`;
}

function toggleChatHistory() {
    const historyList = document.getElementById('chatHistory');
    const toggleBtn = document.getElementById('toggleChatHistory');
    if (historyList.style.display === 'none') {
        fetchChatHistory();
        historyList.style.display = 'block';
        toggleBtn.textContent = translations[currentLanguage]?.hide_history || 'Hide History';
    } else {
        historyList.style.display = 'none';
        toggleBtn.textContent = translations[currentLanguage]?.view_history || 'View History';
    }
}

function updateProgress(step, total, message, showBlink = false) {
    const progressFill = document.querySelector('.progress-fill');
    const statusMessage = document.getElementById('statusMessage');
    const blinkingText = document.getElementById('blinkingText');

    if (!progressFill || !statusMessage) return;

    progressFill.style.width = `${(step / total) * 100}%`;
    statusMessage.textContent = message;

    if (showBlink && !blinkingText) {
        const blinkDiv = document.createElement('div');
        blinkDiv.id = 'blinkingText';
        blinkDiv.className = 'blinking-text';
        blinkDiv.textContent = translations[currentLanguage]?.performing_analysis || 'Processing...';
        statusMessage.insertAdjacentElement('afterend', blinkDiv);
    } else if (!showBlink && blinkingText) {
        blinkingText.remove();
    }
}

function showError(message, isSuccess = false) {
    const errorDiv = document.getElementById('errorMessage');
    if (!errorDiv) return;

    errorDiv.textContent = message;
    errorDiv.className = `error-message${isSuccess ? ' success-message' : ''}`;
    errorDiv.style.display = 'block';
    setTimeout(() => errorDiv.style.display = 'none', 5000);
}

function displayAnalysisResults(data) {
    const resultsContainer = document.getElementById('results');
    const scoresGrid = document.getElementById('scoresGrid');
    const summaryDetails = document.getElementById('summaryDetails');
    const shadowContent = document.getElementById('shadowContent');
    const shadowScore = document.getElementById('shadowScore');
    const evaluationContent = document.getElementById('evaluationContent');
    const chatSection = document.getElementById('chatSection');
    const frequentQuestionsSection = document.getElementById('frequentQuestionsSection');
    const chatInput = document.getElementById('chatInput');
    const sendMessage = document.getElementById('sendMessage');

    if (!data || data.status !== 'success') {
        showError('Analysis failed: ' + (data?.error || 'Unknown error'));
        return;
    }

    // Clear previous content
    scoresGrid.innerHTML = '';
    summaryDetails.innerHTML = '';
    shadowContent.innerHTML = '';
    shadowScore.innerHTML = '';
    evaluationContent.innerHTML = '';

    // Render section scores
    if (data.summary?.structured_analysis) {
        Object.entries(data.summary.structured_analysis).forEach(([key, value]) => {
            if (key !== 'overall_score' && value.content) {
                const score = value.score || 'N/A';
                scoresGrid.innerHTML += `
                    <div class="score-card">
                        <h4>${key.replace(/_/g, ' ').toUpperCase()}</h4>
                        <p>Score: ${score}/10</p>
                        <p>${value.content}</p>
                    </div>
                `;
            }
        });
    }

    // Render summary details
    if (data.summary?.summary) {
        summaryDetails.innerHTML = `
            <h4>Executive Summary</h4>
            <p>${data.summary.summary.executive_summary || 'No executive summary available'}</p>
            <h4>Key Points</h4>
            <ul>${data.summary.summary.key_points ? `<li>${data.summary.summary.key_points.split('. ').filter(p => p).join('</li><li>')}</li>` : '<li>No key points</li>'}</ul>
            <h4>Potential Issues</h4>
            <p>${data.summary.summary.potential_issues || 'No issues identified'}</p>
            <h4>Recommendations</h4>
            <p>${data.summary.summary.recommendations || 'No recommendations'}</p>
        `;
    }

    // Render shadow analysis
    if (data.shadow_analysis) {
        shadowScore.innerHTML = `Accuracy: ${data.shadow_analysis.overall_score ? data.shadow_analysis.overall_score * 10 + '%' : 'N/A'}`;
        let topicsHtml = '';
        if (data.shadow_analysis.topics?.length) {
            topicsHtml = data.shadow_analysis.topics.map(topic => `
                <div class="topic-details">
                    <h4>${topic.topic || 'Unnamed Topic'}</h4>
                    <p><strong>Problems:</strong> ${topic.problems || 'None'}</p>
                    <p><strong>Implications:</strong> ${topic.implications || 'None'}</p>
                    <p><strong>Solutions:</strong> ${topic.solutions || 'None'}</p>
                    <p><strong>Score:</strong> ${topic.score || 'N/A'}/10</p>
                </div>
            `).join('');
        }
        shadowContent.innerHTML = `
            ${topicsHtml || '<p>No topics analyzed</p>'}
            <h4>Summary</h4>
            <p>${data.shadow_analysis.summary || 'No summary available'}</p>
        `;
    }

    // Render evaluation
    if (data.evaluation) {
        let areasHtml = '';
        if (data.evaluation.areas) {
            areasHtml = Object.entries(data.evaluation.areas).map(([area, details]) => `
                <div class="area-details">
                    <h4>${area.replace(/_/g, ' ').toUpperCase()}</h4>
                    <p><strong>Score:</strong> ${details.score || 'N/A'}/10</p>
                    <p><strong>Issues:</strong> ${details.issues?.length ? details.issues.join('; ') : 'None'}</p>
                    <p><strong>Recommendations:</strong> ${details.recommendations?.length ? details.recommendations.join('; ') : 'None'}</p>
                </div>
            `).join('');
        }
        evaluationContent.innerHTML = `
            <p><strong>Overall Score:</strong> ${data.evaluation.overall_score || 'N/A'}/10</p>
            <p><strong>Clarity:</strong> ${data.evaluation.scores?.clarity || 'N/A'}/10</p>
            <p><strong>Completeness:</strong> ${data.evaluation.scores?.completeness || 'N/A'}/10</p>
            <p><strong>Risk Level:</strong> ${data.evaluation.scores?.risk_level || 'N/A'}/10</p>
            <p><strong>Fairness:</strong> ${data.evaluation.scores?.fairness || 'N/A'}/10</p>
            ${areasHtml}
            <h4>Recommendations</h4>
            <p>${data.evaluation.recommendations?.length ? data.evaluation.recommendations.join('; ') : 'No recommendations'}</p>
        `;
    }

    // Enable chat and questions
    chatSection.style.display = 'block';
    frequentQuestionsSection.style.display = 'block';
    chatInput.disabled = false;
    sendMessage.disabled = false;

    resultsContainer.style.display = 'block';
}

document.querySelectorAll('.tab-button').forEach(button => {
    button.addEventListener('click', () => {
        // Remove active class from all buttons
        document.querySelectorAll('.tab-button').forEach(btn => btn.classList.remove('active'));
        // Hide all tab contents
        document.querySelectorAll('.tab-content').forEach(content => content.style.display = 'none');
        // Activate clicked button
        button.classList.add('active');
        // Show corresponding tab content
        const tabId = button.getAttribute('data-tab') + 'Tab';
        document.getElementById(tabId).style.display = 'block';
    });
});

function displayContractSummary(summary) {
    const keyPoints = summary?.key_points?.split('\n').filter(p => p.trim()) || [];
    const potentialIssues = summary?.potential_issues?.split('\n').filter(p => p.trim()) || [];
    const recommendations = summary?.recommendations?.split('\n').filter(p => p.trim()) || [];

    const summaryContent = document.getElementById('summaryContent');
    summaryContent.innerHTML = `
        <div class="summary-section">
            <h3 data-lang-key="executive_summary">${translations[currentLanguage]?.executive_summary || 'Executive Summary'}</h3>
            <p>${(summary?.executive_summary || translations[currentLanguage]?.no_summary || 'No summary available').replace(/</g, '')}</p>
            <div class="summary-details">
                <h4 data-lang-key="key_points">${translations[currentLanguage]?.key_points || 'Key Points'}</h4>
                <ul class="data-list">
                    ${keyPoints.length ? keyPoints.map(point => `<li>${point.replace(/</g, '')}</li>`).join('') : `<li>${translations[currentLanguage]?.no_key_points || 'No key points.'}</li>`}
                </ul>
                <h4 data-lang-key="potential_issues">${translations[currentLanguage]?.potential_issues || 'Potential Issues'}</h4>
                <ul class="data-list">
                    ${potentialIssues.length ? potentialIssues.map(issue => `<li>${issue.replace(/</g, '')}</li>`).join('') : `<li>${translations[currentLanguage]?.no_issues || 'No issues.'}</li>`}
                </ul>
                <h4 data-lang-key="recommendations">${translations[currentLanguage]?.recommendations || 'Recommendations'}</h4>
                <ul class="data-list">
                    ${recommendations.length ? recommendations.map(rec => `<li>${rec.replace(/</g, '')}</li>`).join('') : `<li>${translations[currentLanguage]?.no_recommendations || 'No recommendations'}</li>`}
                </ul>
            </div>
        </div>
    `;
}

function displayScoresGrid(analysis) {
    const scoresHtml = Object.entries(analysis || {})
        .filter(([key]) => key !== 'overall_score')
        .map(([key, value]) => {
            const translatedTitle = translations[currentLanguage]?.marks?.[key] || formatTitle(key);
            return `
                <div class="score-card ${getScoreClass(value?.score)}">
                    <div class="score-header">
                        <h4 data-mark-key="${key}">${translatedTitle}</h4>
                        <div class="score-info">
                            <span class="score-badge">${value?.score || 0}/10</span>
                        </div>
                    </div>
                    ${value?.content ? `<div class="score-content"><p>${value.content.replace(/</g, '')}</p></div>` : ''}
                </div>
            `;
        }).join('');

    const scoresGrid = document.getElementById('scoresGrid');
    if (scoresGrid) scoresGrid.innerHTML = scoresHtml;
}

function displayShadowAnalysis(shadowData) {
    const shadowContent = document.getElementById('shadowContent');
    if (!shadowContent) return;

    shadowContent.innerHTML = `
        <div class="shadow-section">
            <div class="shadow-text">
                ${formatShadowContent(shadowData.content || '')}
            </div>
        </div>
    `;
}

function formatShadowContent(content) {
    if (!content) return `<p>${translations[currentLanguage]?.no_analysis || 'No analysis available'}</p>`;
    return content
        .replace(/</g, '')
        .replace(/>/g, '')
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
    const summaryScore = document.getElementById('summaryScore');
    const shadowScore = document.getElementById('shadowScore');
    if (!summaryScore || !shadowScore) return;

    const overallScore = (evaluation?.overall_score || 0) * 10;
    summaryScore.innerHTML = `
        <div class="score-value">${Math.round(overallScore)}%</div>
        <div class="score-label" data-lang-key="overall_score">${translations[currentLanguage]?.overall_score || 'Overall Score'}</div>
    `;
    shadowScore.innerHTML = `
        <div class="score-value">${Math.round(overallScore)}%</div>
        <div class="score-label" data-lang-key="analysis_accuracy">${translations[currentLanguage]?.analysis_accuracy || 'Analysis Accuracy'}</div>
    `;
}

function getScoreClass(score) {
    if (!score || score <= 3) return 'low-score';
    if (score >= 3) return 'high-score';
    return '';
}

function formatTitle(key) {
    return key.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
}

function displayChatMessage(message, isUser = false) {
    const chatMessages = document.getElementById('chatMessages');
    if (!chatMessages) return;

    const messageDiv = document.createElement('div');
    messageDiv.className = `chat-message ${isUser ? 'user-message' : 'bot-message'}`;
    const timestamp = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

    // Parse Markdown-like formatting
    let formattedMessage = message
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>') // Bold
        .replace(/^\* (.*)$/gm, '<li>$1</li>') // List items
        .replace(/\n\n/g, '</p><p>') // Paragraphs
        .replace(/\n/g, '<br>'); // Line breaks

    // Wrap list items in <ul>
    formattedMessage = formattedMessage.replace(/(<li>.*<\/li>)/s, '<ul>$1</ul>');
    // Ensure paragraphs are properly formatted
    formattedMessage = `<p>${formattedMessage.replace(/<p>\s*<\/p>/g, '')}</p>`;

    messageDiv.innerHTML = `
        <div class="message-content">
            <div class="message-avatar ${isUser ? 'user-avatar' : 'bot-avatar'}">
                ${isUser ? '🙂' : '🤖'}
            </div>
            <div class="message-text">
                ${formattedMessage}
                <span class="message-timestamp">${timestamp}</span>
            </div>
        </div>
    `;

    messageDiv.style.opacity = '0';
    chatMessages.appendChild(messageDiv);
    setTimeout(() => {
        messageDiv.style.opacity = '1';
        messageDiv.style.transform = 'translateY(0)';
    }, 10);

    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function displayTypingIndicator() {
    const chatMessages = document.getElementById('chatMessages');
    if (!chatMessages) return;

    const typingDiv = document.createElement('div');
    typingDiv.id = 'typingIndicator';
    typingDiv.className = 'chat-message bot-message typing-indicator';
    typingDiv.innerHTML = `
        <div class="message-content">
            <div class="message-avatar bot-avatar">🤖</div>
            <div class="message-text">
                <div class="typing-dots">
                    <span></span><span></span><span></span>
                </div>
            </div>
        </div>
    `;
    chatMessages.appendChild(typingDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function removeTypingIndicator() {
    const typingIndicator = document.getElementById('typingIndicator');
    if (typingIndicator) typingIndicator.remove();
}

function autoResizeTextarea() {
    const textarea = document.getElementById('chatInput');
    if (textarea) {
        textarea.style.height = 'auto';
        textarea.style.height = `${Math.min(textarea.scrollHeight, 120)}px`;
    }
}

document.addEventListener('DOMContentLoaded', () => {
    // Set user_id after login
    if (window.location.pathname === '/' && !localStorage.getItem('user_id')) {
        fetch('/auth/check')
            .then(res => res.json())
            .then(data => {
                if (data.authenticated) {
                    localStorage.setItem('user_id', data.user_id || 'authenticated_user');
                    // Check if analysis is complete
                    fetch('/api/check_analysis_status', {
                        headers: { 'X-User-ID': localStorage.getItem('user_id') }
                    })
                        .then(res => res.json())
                        .then(data => {
                            if (data.analysis_complete) {
                                fetchFrequentQuestions();
                                const chatSection = document.getElementById('chatSection');
                                const frequentQuestionsSection = document.getElementById('frequentQuestionsSection');
                                if (chatSection) chatSection.style.display = 'block';
                                if (frequentQuestionsSection) frequentQuestionsSection.style.display = 'block';
                            }
                        });
                } else if (window.location.pathname !== '/auth/login') {
                    window.location.href = '/auth/login';
                }
            });
    }

    const form = document.getElementById('uploadForm');
    if (form) form.addEventListener('submit', handleFileUpload);

    const chatInput = document.getElementById('chatInput');
    const sendButton = document.getElementById('sendMessage');
    if (chatInput) {
        chatInput.addEventListener('keypress', e => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendChatMessage();
            }
        });
        chatInput.addEventListener('input', autoResizeTextarea);
    }
    if (sendButton) sendButton.addEventListener('click', sendChatMessage);

    const languageSelect = document.getElementById('languageSelect');
    if (languageSelect) {
        languageSelect.value = currentLanguage;
        languageSelect.addEventListener('change', changeLanguage);
    }

    const toggleHistoryBtn = document.getElementById('toggleChatHistory');
    if (toggleHistoryBtn) toggleHistoryBtn.addEventListener('click', toggleChatHistory);

    document.querySelectorAll('a[href^="/auth/logout"]').forEach(link => {
        link.addEventListener('click', e => {
            e.preventDefault();
            localStorage.removeItem('user_id');
            window.location.href = '/auth/logout';
        });
    });

    window.addEventListener('beforeunload', endChatSession);

    updateLanguageStrings();
    updateMarksTranslations();
});

