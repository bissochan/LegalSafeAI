// static/js/main.js
let currentLanguage = 'en';
let chatSessionId = null;
let lastAnalysisResults = null;
let currentMode = 'contract';

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

function updateMarksTranslations() {
    const markElements = document.querySelectorAll('[data-mark-key]');
    markElements.forEach(element => {
        const key = element.getAttribute('data-mark-key');
        const translatedText = translations[currentLanguage]?.marks?.[key] || formatTitle(key);
        element.textContent = translatedText;
    });
}

function changeLanguage() {
    const newLanguage = document.getElementById('languageSelect').value;
    if (currentLanguage === newLanguage) return;

    console.log(`Changing language from ${currentLanguage} to ${newLanguage}`);
    currentLanguage = newLanguage;
    localStorage.setItem('preferredLanguage', currentLanguage);

    updateLanguageStrings();
    updateMarksTranslations();

    if (lastAnalysisResults) {
        console.log('Retranslating analysis results');
        retranslateAnalysisResults(currentLanguage);
    } else {
        console.log('No analysis results to retranslate, updating chat language');
        updateChatLanguage(currentLanguage);
    }
}

function disableInputsDuringRetranslation(disable) {
    const languageSelect = document.getElementById('languageSelect');
    const chatInput = document.getElementById('chatInput');
    const sendButton = document.getElementById('sendMessage');
    
    languageSelect.disabled = disable;
    chatInput.disabled = disable;
    sendButton.disabled = disable;
}

async function retranslateAnalysisResults(language) {
    try {
        document.getElementById('analysisStatus').style.display = 'block';
        updateProgress(1, 2, translations[currentLanguage]?.translating || 'Translating analysis...', true);
        disableInputsDuringRetranslation(true);

        console.log(`Sending /retranslate request for ${language}`);
        const response = await fetch('/retranslate', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ language })
        });

        const data = await response.json();
        console.log(`Retranslate response for ${language}:`, data);

        if (!response.ok) {
            console.error(`Retranslation failed with status ${response.status}: ${data.error}`);
            throw new Error(data.error || `Retranslation failed: ${response.status}`);
        }

        if (data.status === 'success') {
            lastAnalysisResults = data;
            displayAnalysisResults(data);
            updateProgress(2, 2, translations[currentLanguage]?.translation_complete || 'Translation complete');
            console.log(`Successfully retranslated to ${language}`);
            await restartChat(language);
        } else {
            console.error(`Translation error for ${language}: ${data.error}`);
            throw new Error(data.error || 'Retranslation failed');
        }
    } catch (error) {
        console.error(`Retranslation error for ${language}:`, error);
        showError(`${translations[currentLanguage]?.retranslation_error || 'Translation error'}: ${error.message}`);
        if (lastAnalysisResults) {
            console.log('Falling back to last analysis results:', lastAnalysisResults);
            displayAnalysisResults(lastAnalysisResults);
        } else {
            document.getElementById('results').style.display = 'none';
        }
    } finally {
        document.getElementById('analysisStatus').style.display = 'none';
        disableInputsDuringRetranslation(false);
    }
}

async function restartChat(language) {
    console.log(`Restarting chat in language: ${language}`);
    await endChatSession();
    if (lastAnalysisResults && lastAnalysisResults.document_text) {
        await initializeChat(lastAnalysisResults.document_text);
        await updateChatLanguage(language);
    } else {
        console.warn('No contract text available to restart chat');
    }
}

async function updateChatLanguage(language) {
    try {
        const response = await fetch('/api/chat/update_language', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ language })
        });

        if (!response.ok) {
            throw new Error(`Chat language update failed: ${response.status}`);
        }

        const data = await response.json();
        if (data.status !== 'success') {
            throw new Error(data.error || 'Chat language update failed');
        }
        console.log(`Chat language updated to ${language}`);
    } catch (error) {
        console.error('Chat language update error:', error);
        showError(`${translations[currentLanguage]?.chat_language_error || 'Chat language error'}: ${error.message}`);
    }
}

async function initializeChat(contractText) {
    const chatMessages = document.getElementById('chatMessages');
    if (chatMessages) chatMessages.innerHTML = '';

    const chatInput = document.getElementById('chatInput');
    const sendButton = document.getElementById('sendMessage');
    chatInput.disabled = true;
    sendButton.disabled = true;

    if (!contractText) {
        console.warn('No contract text for chat initialization');
        return;
    }

    try {
        console.log('Starting chat session');
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
            throw new Error(`Chat start failed: ${response.status}`);
        }

        const data = await response.json();
        if (data.status === 'success') {
            chatSessionId = data.session_id;
            console.log('Chat session started:', chatSessionId);
            chatInput.disabled = false;
            sendButton.disabled = false;
        } else {
            throw new Error(data.error || 'Chat initialization failed');
        }
    } catch (error) {
        console.error('Chat initialization error:', error);
        showError(`${translations[currentLanguage]?.chat_init_error || 'Chat initialization failed'}: ${error.message}`);
        chatInput.disabled = true;
        sendButton.disabled = true;
    }
}

async function sendChatMessage() {
    const chatInput = document.getElementById('chatInput');
    const message = chatInput.value.trim();

    if (!message) return;

    if (!chatSessionId) {
        showError(translations[currentLanguage]?.no_chat_session || 'No active chat session. Please analyze a contract.');
        return;
    }

    displayChatMessage(message, true);
    chatInput.value = '';
    chatInput.disabled = true;
    document.getElementById('sendMessage').disabled = true;

    try {
        const response = await fetch('/api/chat/message', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                message,
                language: currentLanguage
            })
        });

        if (!response.ok) {
            throw new Error(`Chat message failed: ${response.status}`);
        }

        const data = await response.json();
        if (data.status === 'success') {
            displayChatMessage(data.response);
        } else {
            throw new Error(data.error || 'Failed to process message');
        }
    } catch (error) {
        console.error('Chat error:', error);
        displayChatMessage(`${translations[currentLanguage]?.chat_error || 'Error'}: ${error.message}`);
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
    console.log('Handling file upload');

    const resultsContainer = document.getElementById('results');
    resultsContainer.style.display = 'none';

    const fileInput = document.getElementById('contractFile');
    const languageSelect = document.getElementById('languageSelect');

    if (!fileInput.files || fileInput.files.length === 0) {
        showError(translations[currentLanguage]?.no_file_selected || 'Please select a file.');
        return;
    }

    const formData = new FormData();
    formData.append('file', fileInput.files[0]);
    formData.append('language', languageSelect.value);

    document.getElementById('analysisStatus').style.display = 'block';
    updateProgress(1, 4, translations[currentLanguage]?.extracting_text || 'Extracting text...', true);

    try {
        console.log('Sending /api/document/extract request');
        const extractResponse = await fetch('/api/document/extract', {
            method: 'POST',
            body: formData
        });

        if (!extractResponse.ok) {
            const errorData = await extractResponse.json();
            throw new Error(errorData.error || 'Text extraction failed');
        }

        const extractData = await extractResponse.json();
        if (extractData.status !== 'success') {
            throw new Error(extractData.error || 'Text extraction failed');
        }

        updateProgress(2, 4, translations[currentLanguage]?.analyzing_contract || 'Analyzing contract...', true);

        console.log('Sending /analyze request');
        const analyzeResponse = await fetch('/analyze', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
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
        console.log('Analysis response:', analysisData);

        if (analysisData.status === 'success') {
            lastAnalysisResults = analysisData;
            updateProgress(4, 4, translations[currentLanguage]?.analysis_complete || 'Analysis complete');
            displayAnalysisResults(analysisData);
            await initializeChat(analysisData.document_text);
        } else {
            throw new Error(analysisData.error || 'Analysis failed');
        }

    } catch (error) {
        console.error('File upload error:', error);
        showError(`${translations[currentLanguage]?.error_occurred || 'Error'}: ${error.message}`);
    } finally {
        document.getElementById('analysisStatus').style.display = 'none';
    }
}

function updateProgress(step, total, message, showBlink = false) {
    const progressFill = document.querySelector('.progress-fill');
    const statusMessage = document.getElementById('statusMessage');
    const blinkingText = document.getElementById('blinkingText');
    progressFill.style.width = `${(step / total) * 100}%`;
    statusMessage.textContent = message;
    if (showBlink) {
        if (!blinkingText) {
            const blinkDiv = document.createElement('div');
            blinkDiv.id = 'blinkingText';
            blinkDiv.className = 'blinking-text';
            blinkDiv.textContent = translations[currentLanguage]?.performing_analysis || 'Processing...';
            statusMessage.insertAdjacentElement('afterend', blinkDiv);
        } else {
            blinkingText.textContent = translations[currentLanguage]?.performing_analysis || 'Processing...';
        }
    } else if (blinkingText) {
        blinkingText.remove();
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
    console.log('Displaying analysis results:', data);

    if (!data || data.status !== 'success') {
        console.error('Invalid analysis data:', data);
        showError(translations[currentLanguage]?.error_occurred || 'Failed to display results.');
        document.getElementById('results').style.display = 'none';
        return;
    }

    lastAnalysisResults = data;

    localStorage.setItem('analysisData', JSON.stringify({
        contract_text: data.document_text,
        shadow_analysis: data.shadow_analysis,
        summary_analysis: data.summary
    }));

    // Reset UI
    document.getElementById('summaryContent').innerHTML = '';
    document.getElementById('scoresGrid').innerHTML = '';
    document.getElementById('shadowContent').innerHTML = '';

    // Display contract text
    document.getElementById('summaryContent').innerHTML = `
        <div class="summary-section">
            <h3 data-lang-key="contract_text">${translations[currentLanguage]?.contract_text || 'Contract Text'}</h3>
            <pre class="contract-text">${(data.document_text || '').replace(/\n/g, '<br>')}</pre>
        </div>
    `;

    displayContractSummary(data.summary || {});
    displayScoresGrid(data.summary?.structured_analysis || {});
    displayShadowAnalysis({ content: data.shadow_analysis || '' });
    updateScoreBadges(data.evaluation || {});
    updateLanguageStrings();
    updateMarksTranslations();

    document.getElementById('results').style.display = 'block';
    console.log('Results displayed successfully');
}

function displayContractSummary(summary) {
    console.log('Displaying summary:', summary);

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
        .map(([key, value]) => {
            const translatedTitle = translations[currentLanguage]?.marks?.[key] || formatTitle(key);
            return `
                <div class="score-card ${getScoreClass(value.score)}">
                    <div class="score-header">
                        <h4 data-mark-key="${key}">${translatedTitle}</h4>
                        <div class="score-info">
                            <span class="score-badge">${value.score || 0}/10</span>
                        </div>
                    </div>
                    ${value.content ? `<div class="score-content"><p>${value.content}</p></div>` : ''}
                </div>
            `;
        })
        .join('');

    document.getElementById('scoresGrid').innerHTML = scoresHtml;
}

function displayShadowAnalysis(shadowData) {
    const shadowContent = document.getElementById('shadowContent');
    shadowContent.innerHTML = `
        <div class="shadow-section">
            <div class="shadow-text">
                ${formatShadowContent(shadowData.content || '')}
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
    if (!score || score <= 3) return "low-score";
    if (score >= 8) return "high-score";
    return "";
}

function formatTitle(key) {
    return key.replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase());
}

function displayChatMessage(message, isUser = false) {
    const chatMessages = document.getElementById('chatMessages');
    const messageDiv = document.createElement('div');
    messageDiv.className = `chat-message ${isUser ? 'user-message' : 'bot-message'}`;

    const formattedMessage = message
        .split('\n\n')
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
        .join('');

    messageDiv.innerHTML = formattedMessage;
    chatMessages.appendChild(messageDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function switchMode(mode) {
    const contractSection = document.getElementById('contractSection');
    const studentSection = document.getElementById('studentSection');
    const contractBtn = document.getElementById('contractModeBtn');
    const studentBtn = document.getElementById('studentModeBtn');

    localStorage.setItem('currentMode', mode);
    currentMode = mode;

    if (mode === 'contract') {
        contractSection.style.display = 'block';
        studentSection.style.display = 'none';
        contractBtn.classList.add('active');
        studentBtn.classList.remove('active');
    } else {
        contractSection.style.display = 'none';
        studentSection.style.display = 'block';
        contractBtn.classList.remove('active');
        studentBtn.classList.add('active');
    }
}

async function handleStudentSearch(event) {
    event.preventDefault();
    
    const university = document.getElementById('universityInput').value;
    const category = document.getElementById('categorySelect').value;
    const customKeywords = document.getElementById('customKeywords').value;
    
    try {
        const response = await fetch('/api/student/search', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                university,
                category,
                keywords: category === 'custom' ? customKeywords.split(',').map(k => k.trim()) : undefined,
                language: currentLanguage
            })
        });

        if (!response.ok) {
            throw new Error('Search failed');
        }

        const data = await response.json();
        displayStudentResults(data);
    } catch (error) {
        showError(`${translations[currentLanguage]?.error_occurred || 'Search failed'}: ${error.message}`);
    }
}

function displayStudentResults(data) {
    if (data.status !== 'success') {
        showError(data.error || translations[currentLanguage]?.no_results || 'Search failed');
        return;
    }

    const resultsHtml = `
        <div class="card">
            <div class="search-summary">
                <h3 data-lang-key="search_results">Search Results</h3>
                <p data-lang-key="results_for">Results for ${data.university}</p>
                <p data-lang-key="found_results">Found ${data.summary.total_results} relevant results</p>
            </div>
            ${data.results.map(result => `
                <div class="search-result">
                    <h4 class="result-title">
                        <a href="${result.url}" target="_blank">${result.title}</a>
                    </h4>
                    <p class="result-summary">${result.content_summary}</p>
                    <div class="result-meta">
                        <div class="keywords">
                            ${result.matched_keywords.map(kw => `<span class="keyword-tag">${kw}</span>`).join('')}
                        </div>
                        <div class="relevance">
                            <span class="relevance-score">
                                ${translations[currentLanguage]?.relevance_score || 'Relevance'}: ${result.relevance.toFixed(2)}
                            </span>
                        </div>
                    </div>
                </div>
            `).join('')}
        </div>
    `;

    const searchResults = document.getElementById('searchResults');
    searchResults.innerHTML = resultsHtml;
    searchResults.style.display = 'block';
    updateLanguageStrings();
}

document.addEventListener('DOMContentLoaded', () => {
    try {
        const form = document.getElementById('uploadForm');
        if (form) {
            form.addEventListener('submit', handleFileUpload);
            console.log('Form submit handler attached');
        }

        const chatInput = document.getElementById('chatInput');
        const sendButton = document.getElementById('sendMessage');
        if (chatInput) {
            chatInput.addEventListener('keypress', e => {
                if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    sendChatMessage();
                }
            });
        }
        if (sendButton) {
            sendButton.addEventListener('click', sendChatMessage);
        }

        const contractBtn = document.getElementById('contractModeBtn');
        const studentBtn = document.getElementById('studentModeBtn');
        if (contractBtn && studentBtn) {
            contractBtn.addEventListener('click', () => switchMode('contract'));
            studentBtn.addEventListener('click', () => switchMode('student'));
        }

        const savedMode = localStorage.getItem('currentMode') || 'contract';
        switchMode(savedMode);

        const savedLanguage = localStorage.getItem('preferredLanguage');
        if (savedLanguage) {
            currentLanguage = savedLanguage;
            document.getElementById('languageSelect').value = savedLanguage;
            updateLanguageStrings();
            updateMarksTranslations();
        }

        const categorySelect = document.getElementById('categorySelect');
        if (categorySelect) {
            categorySelect.addEventListener('change', function() {
                const customContainer = document.getElementById('customKeywordsContainer');
                customContainer.style.display = this.value === 'custom' ? 'block' : 'none';
            });
        }

        const studentForm = document.getElementById('studentSearchForm');
        if (studentForm) {
            studentForm.addEventListener('submit', handleStudentSearch);
        }

        const languageSelect = document.getElementById('languageSelect');
        if (languageSelect) {
            languageSelect.addEventListener('change', changeLanguage);
        }

        window.addEventListener('beforeunload', endChatSession);
    } catch (error) {
        console.error('DOMContentLoaded error:', error);
    }
});