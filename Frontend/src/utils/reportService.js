// utils/reportsService.js - Comprehensive Reports Service Integration
import api from "./api";
import { API_ENDPOINTS, ERROR_MESSAGES } from "./constants";

/**
 * Comprehensive Reports Service - Business Intelligence for Smart Greenhouse
 * 
 * This service transforms raw greenhouse data into actionable business intelligence.
 * Think of it as your greenhouse's "business analyst" that creates meaningful reports,
 * identifies trends, and provides strategic insights for optimal operations.
 * 
 * Key Capabilities:
 * 1. Multi-service data aggregation and correlation
 * 2. Executive-level dashboard reports with KPIs
 * 3. Operational reports for daily management
 * 4. Financial analysis including cost optimization
 * 5. Compliance and audit reports
 * 6. Predictive analytics and forecasting
 * 7. Customizable report templates and scheduling
 * 8. Export capabilities (PDF, Excel, CSV)
 */

class ReportsService {
  constructor() {
    // Report cache for performance optimization
    this.reportCache = new Map();
    this.cacheConfig = {
      dashboard: { ttl: 300000, key: 'dashboard_report' }, // 5 minutes
      operational: { ttl: 600000, key: 'operational_report' }, // 10 minutes
      financial: { ttl: 1800000, key: 'financial_report' }, // 30 minutes
      compliance: { ttl: 3600000, key: 'compliance_report' } // 1 hour
    };
    
    // Report generation tracking
    this.reportMetrics = {
      totalReports: 0,
      successfulReports: 0,
      averageGenerationTime: 0,
      mostRequestedReports: new Map(),
      lastGenerationTimes: new Map()
    };
    
    // Report templates for different stakeholders
    this.reportTemplates = new Map([
      ['executive_summary', {
        name: 'Executive Summary',
        description: 'High-level KPIs and business metrics',
        sections: ['kpis', 'trends', 'alerts', 'recommendations'],
        audience: 'executives',
        frequency: 'weekly'
      }],
      ['operational_daily', {
        name: 'Daily Operations Report',
        description: 'Daily operational metrics and status',
        sections: ['system_status', 'sensor_data', 'irrigation_events', 'alerts'],
        audience: 'operators',
        frequency: 'daily'
      }],
      ['maintenance_schedule', {
        name: 'Maintenance Schedule Report',
        description: 'Equipment maintenance needs and schedules',
        sections: ['equipment_status', 'maintenance_due', 'performance_trends'],
        audience: 'maintenance',
        frequency: 'weekly'
      }],
      ['financial_analysis', {
        name: 'Financial Analysis Report',
        description: 'Cost analysis and optimization opportunities',
        sections: ['cost_breakdown', 'savings_analysis', 'roi_metrics'],
        audience: 'finance',
        frequency: 'monthly'
      }]
    ]);
  }

  /**
   * Generate comprehensive dashboard report for executives and managers
   * This provides high-level overview of system performance and key metrics
   */
  async generateDashboardReport(options = {}) {
    const {
      period = 7, // days
      includeComparisons = true,
      includeForecasts = true,
      forceRefresh = false
    } = options;

    const cacheKey = `${this.cacheConfig.dashboard.key}_${period}_${includeComparisons}_${includeForecasts}`;
    
    // Check cache unless forced refresh
    if (!forceRefresh && this.isCacheValid(cacheKey, this.cacheConfig.dashboard.ttl)) {
      const cachedReport = this.reportCache.get(cacheKey);
      if (cachedReport) {
        console.log('Using cached dashboard report');
        return cachedReport;
      }
    }

    const startTime = Date.now();

    try {
      console.log(`Generating dashboard report for ${period} days...`);

      // Step 1: Gather data from all relevant services
      const reportData = await this.gatherDashboardData(period, options);
      
      // Step 2: Process and analyze the data
      const analysis = await this.processDashboardAnalysis(reportData, options);
      
      // Step 3: Generate executive-level insights
      const insights = this.generateExecutiveInsights(analysis);
      
      // Step 4: Create actionable recommendations
      const recommendations = this.generateExecutiveRecommendations(analysis);
      
      // Step 5: Compile comprehensive dashboard report
      const dashboardReport = {
        report_type: 'dashboard',
        generated_at: new Date().toISOString(),
        period: {
          days: period,
          start_date: new Date(Date.now() - period * 24 * 60 * 60 * 1000).toISOString(),
          end_date: new Date().toISOString()
        },
        
        // Executive Summary Section
        executive_summary: {
          key_metrics: this.extractKeyMetrics(analysis),
          performance_highlights: insights.highlights,
          critical_alerts: insights.alerts,
          overall_health_score: this.calculateOverallHealthScore(analysis)
        },
        
        // Operational Performance Section
        operational_performance: {
          system_uptime: analysis.system?.uptime_percentage || 0,
          irrigation_efficiency: analysis.irrigation?.efficiency_score || 0,
          sensor_reliability: analysis.sensors?.reliability_score || 0,
          automation_effectiveness: analysis.automation?.effectiveness_score || 0
        },
        
        // Financial Performance Section
        financial_performance: {
          water_costs: analysis.costs?.water_usage || 0,
          energy_costs: analysis.costs?.energy_usage || 0,
          estimated_savings: analysis.costs?.total_savings || 0,
          roi_metrics: analysis.financial?.roi || {}
        },
        
        // Trends and Patterns Section
        trends_analysis: {
          growth_trends: analysis.trends?.plant_growth || [],
          usage_patterns: analysis.trends?.resource_usage || [],
          efficiency_trends: analysis.trends?.system_efficiency || [],
          seasonal_adjustments: analysis.trends?.seasonal_patterns || []
        },
        
        // Predictive Insights Section
        predictive_insights: includeForecasts ? {
          next_week_forecast: analysis.forecasts?.weekly || {},
          maintenance_predictions: analysis.forecasts?.maintenance || [],
          optimization_opportunities: analysis.forecasts?.optimization || []
        } : null,
        
        recommendations: recommendations,
        
        // Report Metadata
        metadata: {
          data_sources: reportData.sources,
          generation_time_ms: Date.now() - startTime,
          data_freshness: this.assessDataFreshness(reportData),
          confidence_level: this.calculateReportConfidence(analysis)
        }
      };

      // Cache the report
      this.reportCache.set(cacheKey, {
        success: true,
        data: dashboardReport,
        cached_at: Date.now()
      });

      // Update metrics
      this.updateReportMetrics('dashboard', startTime);

      return {
        success: true,
        data: dashboardReport
      };

    } catch (error) {
      console.error('Error generating dashboard report:', error);

      // Update failure metrics
      this.reportMetrics.totalReports++;

      return {
        success: false,
        error: error.message || ERROR_MESSAGES.SERVER_ERROR,
        fallback_data: await this.generateFallbackDashboard(period),
        recovery: this.generateRecoveryOptions('dashboard_report', error)
      };
    }
  }

  /**
   * Generate operational report for daily management activities
   * This provides detailed operational insights for greenhouse managers
   */
  async generateOperationalReport(options = {}) {
    const {
      date = new Date().toISOString().split('T')[0], // Today by default
      includeDetails = true,
      includeRecommendations = true,
      forceRefresh = false
    } = options;

    const cacheKey = `${this.cacheConfig.operational.key}_${date}_${includeDetails}`;
    
    if (!forceRefresh && this.isCacheValid(cacheKey, this.cacheConfig.operational.ttl)) {
      const cachedReport = this.reportCache.get(cacheKey);
      if (cachedReport) {
        console.log('Using cached operational report');
        return cachedReport;
      }
    }

    const startTime = Date.now();

    try {
      console.log(`Generating operational report for ${date}...`);

      // Gather operational data for the specified date
      const operationalData = await this.gatherOperationalData(date, options);
      
      // Process operational analysis
      const analysis = await this.processOperationalAnalysis(operationalData, options);
      
      // Generate operational report
      const operationalReport = {
        report_type: 'operational',
        generated_at: new Date().toISOString(),
        report_date: date,
        
        // System Status Section
        system_status: {
          overall_health: analysis.system?.health_status || 'unknown',
          active_alerts: analysis.alerts?.active || [],
          resolved_issues: analysis.alerts?.resolved || [],
          uptime_percentage: analysis.system?.uptime || 0
        },
        
        // Sensor Performance Section
        sensor_performance: {
          data_quality: analysis.sensors?.quality_score || 0,
          sensor_readings: analysis.sensors?.current_readings || {},
          trend_analysis: analysis.sensors?.trends || {},
          calibration_status: analysis.sensors?.calibration || {}
        },
        
        // Irrigation Activities Section
        irrigation_activities: {
          total_events: analysis.irrigation?.event_count || 0,
          total_runtime: analysis.irrigation?.total_runtime || 0,
          water_usage: analysis.irrigation?.water_consumed || 0,
          efficiency_metrics: analysis.irrigation?.efficiency || {},
          schedule_adherence: analysis.irrigation?.schedule_performance || {}
        },
        
        // Environmental Conditions Section
        environmental_conditions: {
          temperature_range: analysis.environment?.temperature || {},
          humidity_levels: analysis.environment?.humidity || {},
          light_conditions: analysis.environment?.light || {},
          soil_moisture_levels: analysis.environment?.soil_moisture || {}
        },
        
        // AI and Automation Section
        ai_automation: {
          recommendations_generated: analysis.ai?.recommendation_count || 0,
          recommendations_applied: analysis.ai?.applied_count || 0,
          automation_events: analysis.automation?.events || [],
          decision_accuracy: analysis.ai?.accuracy_score || 0
        },
        
        // Daily Recommendations
        daily_recommendations: includeRecommendations ? 
          this.generateOperationalRecommendations(analysis) : [],
        
        // Performance Metrics
        performance_metrics: {
          water_efficiency: analysis.performance?.water_efficiency || 0,
          energy_efficiency: analysis.performance?.energy_efficiency || 0,
          system_reliability: analysis.performance?.reliability || 0,
          automation_effectiveness: analysis.performance?.automation || 0
        },
        
        metadata: {
          data_sources: operationalData.sources,
          generation_time_ms: Date.now() - startTime,
          data_completeness: this.assessDataCompleteness(operationalData)
        }
      };

      // Cache the report
      this.reportCache.set(cacheKey, {
        success: true,
        data: operationalReport,
        cached_at: Date.now()
      });

      this.updateReportMetrics('operational', startTime);

      return {
        success: true,
        data: operationalReport
      };

    } catch (error) {
      console.error('Error generating operational report:', error);

      return {
        success: false,
        error: error.message || ERROR_MESSAGES.SERVER_ERROR,
        fallback_data: await this.generateFallbackOperational(date),
        recovery: this.generateRecoveryOptions('operational_report', error)
      };
    }
  }

  /**
   * Generate financial analysis report for cost optimization
   * This provides detailed financial insights and optimization opportunities
   */
  async generateFinancialReport(options = {}) {
    const {
      period = 30, // days
      includeCostBreakdown = true,
      includeROIAnalysis = true,
      includeProjections = true
    } = options;

    const startTime = Date.now();

    try {
      console.log(`Generating financial report for ${period} days...`);

      // Gather financial data
      const financialData = await this.gatherFinancialData(period, options);
      
      // Process financial analysis
      const analysis = await this.processFinancialAnalysis(financialData, options);
      
      // Generate financial report
      const financialReport = {
        report_type: 'financial',
        generated_at: new Date().toISOString(),
        analysis_period: {
          days: period,
          start_date: new Date(Date.now() - period * 24 * 60 * 60 * 1000).toISOString(),
          end_date: new Date().toISOString()
        },
        
        // Cost Overview Section
        cost_overview: {
          total_costs: analysis.costs?.total || 0,
          water_costs: analysis.costs?.water || 0,
          energy_costs: analysis.costs?.energy || 0,
          maintenance_costs: analysis.costs?.maintenance || 0,
          cost_per_day: analysis.costs?.daily_average || 0
        },
        
        // Cost Breakdown Section
        cost_breakdown: includeCostBreakdown ? {
          operational_costs: analysis.breakdown?.operational || {},
          infrastructure_costs: analysis.breakdown?.infrastructure || {},
          variable_costs: analysis.breakdown?.variable || {},
          fixed_costs: analysis.breakdown?.fixed || {}
        } : null,
        
        // Savings Analysis Section
        savings_analysis: {
          actual_savings: analysis.savings?.actual || 0,
          potential_savings: analysis.savings?.potential || 0,
          efficiency_gains: analysis.savings?.efficiency || {},
          automation_savings: analysis.savings?.automation || 0
        },
        
        // ROI Analysis Section
        roi_analysis: includeROIAnalysis ? {
          system_roi: analysis.roi?.system || 0,
          automation_roi: analysis.roi?.automation || 0,
          payback_period: analysis.roi?.payback_months || 0,
          investment_metrics: analysis.roi?.metrics || {}
        } : null,
        
        // Cost Optimization Opportunities
        optimization_opportunities: {
          water_usage_optimization: analysis.optimization?.water || [],
          energy_efficiency_improvements: analysis.optimization?.energy || [],
          maintenance_cost_reduction: analysis.optimization?.maintenance || [],
          automation_expansion: analysis.optimization?.automation || []
        },
        
        // Financial Projections
        projections: includeProjections ? {
          monthly_forecast: analysis.projections?.monthly || {},
          annual_projections: analysis.projections?.annual || {},
          break_even_analysis: analysis.projections?.breakeven || {}
        } : null,
        
        // Benchmarking
        benchmarking: {
          industry_comparison: analysis.benchmarks?.industry || {},
          efficiency_rankings: analysis.benchmarks?.efficiency || {},
          cost_competitiveness: analysis.benchmarks?.cost || {}
        },
        
        recommendations: this.generateFinancialRecommendations(analysis),
        
        metadata: {
          data_sources: financialData.sources,
          generation_time_ms: Date.now() - startTime,
          currency: 'VND',
          exchange_rates: analysis.exchange_rates || {}
        }
      };

      this.updateReportMetrics('financial', startTime);

      return {
        success: true,
        data: financialReport
      };

    } catch (error) {
      console.error('Error generating financial report:', error);

      return {
        success: false,
        error: error.message || ERROR_MESSAGES.SERVER_ERROR,
        fallback_data: await this.generateFallbackFinancial(period)
      };
    }
  }

  /**
   * Gather comprehensive data from all services for dashboard reporting
   * This aggregates data from sensors, devices, AI, and user management services
   */
  async gatherDashboardData(period, options) {
    const sources = [];
    const data = {};

    try {
      // Import services dynamically to avoid circular dependencies
      const [sensorService, deviceControlService, aiAnalyticsService] = await Promise.all([
        import('./sensorService').then(module => module.default),
        import('./deviceControlService').then(module => module.default),
        import('./aiAnalyticsService').then(module => module.default)
      ]);

      sources.push('sensor_service', 'device_control_service', 'ai_analytics_service');

      // Gather sensor data and trends
      console.log('Gathering sensor data for dashboard...');
      const sensorData = await sensorService.fetchCurrentSensorData();
      const sensorHistory = await sensorService.fetchHistoricalData({ hours: period * 24 });
      
      data.sensors = {
        current: sensorData,
        historical: sensorHistory,
        trends: this.calculateSensorTrends(sensorHistory)
      };

      // Gather system status and irrigation data
      console.log('Gathering system status for dashboard...');
      const systemStatus = await deviceControlService.getIrrigationStatus();
      const scheduleStatus = await deviceControlService.getScheduleStatus();
      
      data.system = {
        status: systemStatus.success ? systemStatus.data : null,
        schedules: scheduleStatus.success ? scheduleStatus.data : null,
        performance: this.calculateSystemPerformance(systemStatus.data)
      };

      // Gather AI analytics and insights
      if (options.includeForecasts || options.includeComparisons) {
        console.log('Gathering AI analytics for dashboard...');
        const analyticsData = await aiAnalyticsService.getHistoricalAnalysis({
          period: 'weekly',
          days: period,
          includeComparisons: options.includeComparisons,
          includePredictions: options.includeForecasts
        });
        
        data.analytics = analyticsData.success ? analyticsData.data : null;
      }

    } catch (error) {
      console.error('Error gathering dashboard data:', error);
      data.error = error.message;
    }

    return {
      data,
      sources,
      timestamp: new Date().toISOString()
    };
  }

  /**
   * Generate executive-level insights from analysis data
   * This transforms technical data into business insights
   */
  generateExecutiveInsights(analysis) {
    const insights = {
      highlights: [],
      alerts: [],
      opportunities: []
    };

    // Performance highlights
    if (analysis.system?.uptime_percentage > 95) {
      insights.highlights.push({
        type: 'system_reliability',
        message: `Excellent system uptime: ${analysis.system.uptime_percentage.toFixed(1)}%`,
        impact: 'positive'
      });
    }

    if (analysis.costs?.total_savings > 0) {
      insights.highlights.push({
        type: 'cost_savings',
        message: `Generated ${analysis.costs.total_savings.toLocaleString()} VND in savings`,
        impact: 'positive'
      });
    }

    // Critical alerts
    if (analysis.system?.uptime_percentage < 90) {
      insights.alerts.push({
        type: 'system_reliability',
        message: `Low system uptime: ${analysis.system.uptime_percentage.toFixed(1)}%`,
        severity: 'high',
        action: 'Investigate system reliability issues'
      });
    }

    if (analysis.irrigation?.efficiency_score < 60) {
      insights.alerts.push({
        type: 'irrigation_efficiency',
        message: `Below-average irrigation efficiency: ${analysis.irrigation.efficiency_score}%`,
        severity: 'medium',
        action: 'Review irrigation schedules and sensor calibration'
      });
    }

    // Optimization opportunities
    if (analysis.costs?.potential_savings > 0) {
      insights.opportunities.push({
        type: 'cost_optimization',
        message: `Potential additional savings: ${analysis.costs.potential_savings.toLocaleString()} VND`,
        action: 'Implement suggested optimization measures'
      });
    }

    return insights;
  }

  /**
   * Update report generation metrics for performance monitoring
   */
  updateReportMetrics(reportType, startTime) {
    const generationTime = Date.now() - startTime;
    
    this.reportMetrics.totalReports++;
    this.reportMetrics.successfulReports++;
    
    // Update average generation time
    const currentAvg = this.reportMetrics.averageGenerationTime;
    const newAvg = (currentAvg * (this.reportMetrics.successfulReports - 1) + generationTime) / 
                   this.reportMetrics.successfulReports;
    this.reportMetrics.averageGenerationTime = Math.round(newAvg);
    
    // Track most requested reports
    const currentCount = this.reportMetrics.mostRequestedReports.get(reportType) || 0;
    this.reportMetrics.mostRequestedReports.set(reportType, currentCount + 1);
    
    // Track generation times by report type
    this.reportMetrics.lastGenerationTimes.set(reportType, generationTime);
    
    console.log(`${reportType} report generated in ${generationTime}ms`);
  }

  /**
   * Check if cached report is still valid
   */
  isCacheValid(key, ttl) {
    const cached = this.reportCache.get(key);
    if (!cached) return false;
    
    const age = Date.now() - (cached.cached_at || 0);
    return age < ttl;
  }

  /**
   * Get comprehensive reports service analytics
   */
  getReportsAnalytics() {
    return {
      ...this.reportMetrics,
      cache_performance: {
        cache_size: this.reportCache.size,
        hit_rate: this.calculateCacheHitRate()
      },
      available_templates: Array.from(this.reportTemplates.entries()).map(([key, template]) => ({
        id: key,
        name: template.name,
        description: template.description,
        audience: template.audience,
        frequency: template.frequency
      })),
      last_updated: new Date().toISOString()
    };
  }

  /**
   * Calculate cache hit rate for performance monitoring
   */
  calculateCacheHitRate() {
    if (this.reportMetrics.totalReports === 0) return 0;
    
    // Simplified cache hit rate calculation
    const cacheSize = this.reportCache.size;
    const totalRequests = this.reportMetrics.totalReports;
    
    return Math.round((cacheSize / Math.max(totalRequests, 1)) * 100);
  }
}

// Create and export singleton instance
const reportsService = new ReportsService();

export default reportsService;