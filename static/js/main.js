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
    
    currentLanguage = newLanguage;
    localStorage.setItem('preferredLanguage', currentLanguage);
    
    updateLanguageStrings();
    updateMarksTranslations();

    if (lastAnalysisResults) {
        retranslateAnalysisResults(currentLanguage);
    }

    updateChatLanguage(currentLanguage);
}

async function retranslateAnalysisResults(language) {
    try {
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
    if (!chatSessionId) return;

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
    console.log('handleFileUpload triggered');

    const resultsContainer = document.getElementById('results');
    resultsContainer.style.display = 'none';

    const fileInput = document.getElementById('contractFile');
    const languageSelect = document.getElementById('languageSelect');

    if (!fileInput.files || fileInput.files.length === 0) {
        showError(translations[currentLanguage]?.no_file_selected || 'Please select a file to analyze');
        return;
    }

    const formData = new FormData();
    formData.append('file', fileInput.files[0]);
    formData.append('language', languageSelect.value);

    document.getElementById('analysisStatus').style.display = 'block';
    updateProgress(1, 4, translations[currentLanguage]?.extracting_text || 'Extracting text from document...');

    try {
        console.log('Sending /api/document/extract request');
        const extractResponse = await fetch('/api/document/extract', {
            method: 'POST',
            body: formData
        });

        console.log('Extract response status:', extractResponse.status);
        if (!extractResponse.ok) {
            const errorData = await extractResponse.json();
            throw new Error(errorData.error || 'Failed to extract text');
        }

        const extractData = await extractResponse.json();
        console.log('Extracted data:', extractData);

        if (extractData.status !== 'success') {
            throw new Error(extractData.error || 'Text extraction failed');
        }

        updateProgress(2, 4, translations[currentLanguage]?.analyzing_contract || 'Analyzing contract...');

        console.log('Sending /analyze request');
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

        console.log('Analyze response status:', analyzeResponse.status);
        if (!analyzeResponse.ok) {
            const errorData = await analyzeResponse.json();
            throw new Error(errorData.error || 'Analysis failed');
        }

        const analysisData = await analyzeResponse.json();
        console.log('Analysis data:', analysisData);

        if (analysisData.status === 'success') {
            updateProgress(4, 4, translations[currentLanguage]?.analysis_complete || 'Analysis complete');
            displayAnalysisResults(analysisData);
        } else {
            throw new Error(analysisData.error || 'Analysis failed');
        }

    } catch (error) {
        console.error('File upload error:', error);
        showError(error.message);
        resultsContainer.style.display = 'none';
    } finally {
        document.getElementById('analysisStatus').style.display = 'none';
    }
}

function updateProgress(step, total, message) {
    const progressFill = document.querySelector('.progress-fill');
    const statusMessage = document.getElementById('statusMessage');
    progressFill.style.width = `${(step / total) * 100}%`;
    statusMessage.textContent = message;
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
        showError(translations[currentLanguage]?.error_occurred || 'Failed to process analysis results');
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
    updateLanguageStrings();
    updateMarksTranslations();

    document.getElementById('results').style.display = 'block';
}

function displayContractSummary(summary) {
    console.log('Displaying contract summary:', summary);

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
                            <span class="score-badge">${value.score}/10</span>
                        </div>
                    </div>
                    ${value.content ? `
                        <div class="score-content">
                            <p>${value.content}</p>
                        </div>
                    ` : ''}
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
    const searchResults = document.getElementById('searchResults');
    
    try {
        const response = await fetch('/api/student/search', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                university: university,
                category: category,
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
        showError(translations[currentLanguage]?.error_occurred || 'Search failed: ' + error.message);
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
                            ${result.matched_keywords.map(kw => 
                                `<span class="keyword-tag">${kw}</span>`
                            ).join('')}
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

        const contractBtn = document.getElementById('contractModeBtn');
        const studentBtn = document.getElementById('studentModeBtn');
        if (contractBtn && studentBtn) {
            contractBtn.addEventListener('click', () => {
                console.log('Contract mode button clicked');
                switchMode('contract');
            });
            studentBtn.addEventListener('click', () => {
                console.log('Student mode button clicked');
                switchMode('student');
            });
            console.log('Mode toggle handlers attached');
        } else {
            console.error('Mode toggle buttons not found!');
        }

        const savedMode = localStorage.getItem('currentMode') || 'contract';
        switchMode(savedMode);

        const savedLanguage = localStorage.getItem('preferredLanguage');
        if (savedLanguage) {
            currentLanguage = savedLanguage;
            document.getElementById('languageSelect').value = savedLanguage;
        }

        updateLanguageStrings();
        updateMarksTranslations();

        initializeChat();

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
            console.log('Student search form handler attached');
        } else {
            console.error('Student search form not found!');
        }

        window.addEventListener('beforeunload', endChatSession);
    } catch (error) {
        console.error('DOMContentLoaded error:', error);
    }
});