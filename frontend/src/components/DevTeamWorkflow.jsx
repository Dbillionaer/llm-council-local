import { useState, useEffect } from 'react';
import './DevTeamWorkflow.css';

/**
 * DevTeamWorkflow - Display component for mcp-dev-team workflow progress.
 * 
 * Shows a gold-colored parent frame with:
 * - Plan validation UI with refine/approve buttons
 * - Color-coded child frames for progress reports:
 *   - Blue: Expectations met
 *   - Red: Failed test / expectations
 *   - Green: Process completed
 * - Metrics and status updates
 * 
 * Props:
 * - workflowData: Object with plan, progress_reports, status, etc.
 * - onUserResponse: Callback when user responds (approved, refine, or feedback)
 * - isComplete: Whether the workflow is complete
 */
export default function DevTeamWorkflow({ 
  workflowData = {}, 
  onUserResponse = null,
  isComplete = false 
}) {
  const [isExpanded, setIsExpanded] = useState(!isComplete);
  const [userFeedback, setUserFeedback] = useState('');
  const [expandedReports, setExpandedReports] = useState({});

  // Auto-collapse when complete
  useEffect(() => {
    if (isComplete) {
      setIsExpanded(false);
    }
  }, [isComplete]);

  const {
    project_name = 'Unknown Project',
    status = 'working',
    task_list = [],
    summary = '',
    progress_reports = [],
    metrics = {},
    awaiting_response = false
  } = workflowData;

  // Get status color for progress report
  const getStatusColor = (reportStatus) => {
    switch (reportStatus) {
      case 'success':
        return 'blue'; // Expectations met
      case 'failed':
        return 'red';  // Failed test
      case 'complete':
        return 'green'; // Process completed
      case 'working':
      default:
        return 'gray';  // In progress
    }
  };

  // Get status icon
  const getStatusIcon = (reportStatus) => {
    switch (reportStatus) {
      case 'success':
        return '✅';
      case 'failed':
        return '❌';
      case 'complete':
        return '🎉';
      case 'working':
      default:
        return '⏳';
    }
  };

  const handleApprove = () => {
    if (onUserResponse) {
      onUserResponse('approved');
    }
  };

  const handleRefine = () => {
    if (onUserResponse) {
      onUserResponse('refine');
    }
  };

  const handleSubmitFeedback = () => {
    if (onUserResponse && userFeedback.trim()) {
      onUserResponse(userFeedback.trim());
      setUserFeedback('');
    }
  };

  const toggleReportExpanded = (index) => {
    setExpandedReports(prev => ({
      ...prev,
      [index]: !prev[index]
    }));
  };

  return (
    <div className={`dev-team-workflow ${isExpanded ? 'expanded' : 'collapsed'}`}>
      {/* Gold header */}
      <div 
        className="dev-team-header"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <span className="dev-team-icon">{isExpanded ? '▼' : '▶'}</span>
        <span className="dev-team-label">🏗️ MCP Dev Team</span>
        <span className="dev-team-project">{project_name}</span>
        {status === 'awaiting_plan_validation' && (
          <span className="dev-team-status awaiting">⏸️ Awaiting Input</span>
        )}
        {status === 'completed' && (
          <span className="dev-team-status completed">✅ Complete</span>
        )}
        {status === 'working' && (
          <span className="dev-team-status working">
            <span className="mini-spinner"></span> Working
          </span>
        )}
      </div>

      {isExpanded && (
        <div className="dev-team-content">
          {/* Plan Validation Section */}
          {(status === 'awaiting_plan_validation' || awaiting_response) && (
            <div className="dev-team-plan-validation">
              <div className="plan-validation-header">
                📋 Plan Review Required
              </div>
              
              {summary && (
                <div className="plan-summary">
                  <strong>Summary:</strong> {summary}
                </div>
              )}
              
              {task_list.length > 0 && (
                <div className="plan-tasks">
                  <div className="plan-tasks-header">
                    Tasks ({task_list.length}):
                  </div>
                  <div className="plan-tasks-list">
                    {task_list.map((task, idx) => (
                      <div key={task.id || idx} className={`plan-task ${task.type}`}>
                        <span className="task-id">{task.id || idx + 1}.</span>
                        <span className={`task-type ${task.type}`}>
                          {task.type === 'develop' ? '🔨' : task.type === 'test' ? '🧪' : '🔍'}
                        </span>
                        <span className="task-desc">{task.description}</span>
                        {task.expectations && task.expectations.length > 0 && (
                          <div className="task-expectations">
                            {task.expectations.map((exp, i) => (
                              <div key={i} className="expectation">• {exp}</div>
                            ))}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Action buttons */}
              {onUserResponse && (
                <div className="plan-actions">
                  <button 
                    className="plan-btn approve"
                    onClick={handleApprove}
                  >
                    ✓ Approved
                  </button>
                  <button 
                    className="plan-btn refine"
                    onClick={handleRefine}
                  >
                    ↻ Refine
                  </button>
                  <div className="plan-feedback">
                    <input
                      type="text"
                      placeholder="Or provide specific feedback..."
                      value={userFeedback}
                      onChange={(e) => setUserFeedback(e.target.value)}
                      onKeyDown={(e) => e.key === 'Enter' && handleSubmitFeedback()}
                    />
                    <button 
                      className="plan-btn feedback"
                      onClick={handleSubmitFeedback}
                      disabled={!userFeedback.trim()}
                    >
                      Send
                    </button>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Progress Reports */}
          {progress_reports.length > 0 && (
            <div className="dev-team-progress">
              <div className="progress-header">
                📊 Progress ({progress_reports.length} updates)
              </div>
              <div className="progress-list">
                {progress_reports.map((report, idx) => (
                  <div 
                    key={idx} 
                    className={`progress-report ${getStatusColor(report.status)}`}
                    onClick={() => toggleReportExpanded(idx)}
                  >
                    <div className="report-header">
                      <span className="report-icon">{getStatusIcon(report.status)}</span>
                      <span className="report-message">{report.message}</span>
                      <span className="report-expand">{expandedReports[idx] ? '▼' : '▶'}</span>
                    </div>
                    
                    {expandedReports[idx] && (
                      <div className="report-details">
                        <div className="report-timestamp">
                          {new Date(report.timestamp).toLocaleString()}
                        </div>
                        {report.metrics && Object.keys(report.metrics).length > 0 && (
                          <div className="report-metrics">
                            {Object.entries(report.metrics).map(([key, val]) => (
                              <div key={key} className="metric">
                                <span className="metric-key">{key.replace(/_/g, ' ')}:</span>
                                <span className="metric-value">{val}</span>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Final Metrics */}
          {metrics && Object.keys(metrics).length > 0 && (
            <div className="dev-team-metrics">
              <div className="metrics-header">📈 Final Metrics</div>
              <div className="metrics-grid">
                {Object.entries(metrics).map(([key, val]) => (
                  <div key={key} className="metric-card">
                    <div className="metric-value">{val}</div>
                    <div className="metric-label">{key.replace(/_/g, ' ')}</div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
