// React Component Example for Streaming API
import React, { useState, useRef } from 'react';

const StreamingBadgeGenerator = () => {
  const [content, setContent] = useState('');
  const [isGenerating, setIsGenerating] = useState(false);
  const [streamingText, setStreamingText] = useState('');
  const [finalResponse, setFinalResponse] = useState(null);
  const [error, setError] = useState(null);
  const [status, setStatus] = useState('');
  
  const abortControllerRef = useRef(null);

  const API_BASE_URL = 'http://localhost:8001/api/v1';

  const startStreamingGeneration = async () => {
    if (isGenerating) return;
    
    if (!content.trim()) {
      alert('Please enter course content');
      return;
    }
    
    setIsGenerating(true);
    setStreamingText('');
    setFinalResponse(null);
    setError(null);
    setStatus('Starting generation...');
    
    // Create abort controller for cancellation
    abortControllerRef.current = new AbortController();
    
    const requestBody = {
      content: content,
      temperature: 0.2,
      max_tokens: 1024
    };
    
    try {
      const response = await fetch(`${API_BASE_URL}/generate/stream`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestBody),
        signal: abortControllerRef.current.signal
      });
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      // Handle streaming response
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      
      while (true) {
        const { done, value } = await reader.read();
        
        if (done) break;
        
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop(); // Keep incomplete line in buffer
        
        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6));
              handleStreamChunk(data);
            } catch (e) {
              console.error('Error parsing SSE data:', e);
            }
          }
        }
      }
      
    } catch (error) {
      if (error.name === 'AbortError') {
        setStatus('Generation cancelled.');
      } else {
        console.error('Streaming error:', error);
        setError(`Streaming failed: ${error.message}`);
      }
    } finally {
      setIsGenerating(false);
      abortControllerRef.current = null;
    }
  };
  
  const handleStreamChunk = (chunk) => {
    switch (chunk.type) {
      case 'token':
        setStreamingText(prev => prev + chunk.content);
        setStatus('Generating...');
        break;
        
      case 'final':
        setStatus('Generation completed!');
        setFinalResponse(chunk.content);
        break;
        
      case 'error':
        setError(chunk.content);
        break;
    }
  };
  
  const stopGeneration = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
  };
  
  const clearResponse = () => {
    setStreamingText('');
    setFinalResponse(null);
    setError(null);
    setStatus('');
  };

  return (
    <div className="streaming-badge-generator">
      <h2>🏆 Streaming Badge Generator</h2>
      
      <div className="form-group">
        <label htmlFor="content">Course Content:</label>
        <textarea
          id="content"
          value={content}
          onChange={(e) => setContent(e.target.value)}
          placeholder="Enter course content to generate badge metadata from..."
          rows={6}
          disabled={isGenerating}
        />
      </div>
      
      <div className="button-group">
        <button 
          onClick={startStreamingGeneration}
          disabled={isGenerating}
          className="btn-primary"
        >
          {isGenerating ? 'Generating...' : 'Generate Badge (Streaming)'}
        </button>
        
        <button 
          onClick={stopGeneration}
          disabled={!isGenerating}
          className="btn-secondary"
        >
          Stop Generation
        </button>
        
        <button 
          onClick={clearResponse}
          disabled={isGenerating}
          className="btn-outline"
        >
          Clear Response
        </button>
      </div>
      
      {status && (
        <div className="status">
          {status}
        </div>
      )}
      
      {streamingText && (
        <div className="streaming-container">
          <h3>Live Generation:</h3>
          <div className="streaming-text">
            {streamingText}
          </div>
        </div>
      )}
      
      {finalResponse && (
        <div className="final-response">
          <h3>Final JSON Response:</h3>
          <pre className="json-display">
            {JSON.stringify(finalResponse, null, 2)}
          </pre>
        </div>
      )}
      
      {error && (
        <div className="error">
          <h3>Error:</h3>
          <p>{error}</p>
        </div>
      )}
    </div>
  );
};

export default StreamingBadgeGenerator;

// CSS Styles (add to your CSS file)
const styles = `
.streaming-badge-generator {
  max-width: 800px;
  margin: 0 auto;
  padding: 20px;
}

.form-group {
  margin-bottom: 20px;
}

.form-group label {
  display: block;
  margin-bottom: 5px;
  font-weight: bold;
}

.form-group textarea {
  width: 100%;
  padding: 10px;
  border: 1px solid #ddd;
  border-radius: 5px;
  font-size: 14px;
  resize: vertical;
}

.button-group {
  margin-bottom: 20px;
}

.button-group button {
  margin-right: 10px;
  padding: 10px 20px;
  border: none;
  border-radius: 5px;
  cursor: pointer;
  font-size: 14px;
}

.btn-primary {
  background-color: #007bff;
  color: white;
}

.btn-primary:hover:not(:disabled) {
  background-color: #0056b3;
}

.btn-secondary {
  background-color: #6c757d;
  color: white;
}

.btn-outline {
  background-color: transparent;
  color: #007bff;
  border: 1px solid #007bff;
}

.btn-outline:hover:not(:disabled) {
  background-color: #007bff;
  color: white;
}

button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.status {
  margin-bottom: 15px;
  font-style: italic;
  color: #6c757d;
}

.streaming-container {
  margin-bottom: 20px;
}

.streaming-text {
  background-color: #2d3748;
  color: #e2e8f0;
  padding: 15px;
  border-radius: 5px;
  font-family: 'Courier New', monospace;
  white-space: pre-wrap;
  min-height: 100px;
  max-height: 400px;
  overflow-y: auto;
}

.final-response {
  background-color: #d4edda;
  border: 1px solid #c3e6cb;
  padding: 15px;
  border-radius: 5px;
  margin-bottom: 20px;
}

.json-display {
  background-color: #f8f9fa;
  border: 1px solid #dee2e6;
  padding: 15px;
  border-radius: 5px;
  font-family: 'Courier New', monospace;
  white-space: pre-wrap;
  max-height: 300px;
  overflow-y: auto;
}

.error {
  background-color: #f8d7da;
  border: 1px solid #f5c6cb;
  color: #721c24;
  padding: 15px;
  border-radius: 5px;
  margin-bottom: 20px;
}
`;
