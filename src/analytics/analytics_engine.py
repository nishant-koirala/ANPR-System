"""
Analytics Engine for ANPR System
Provides trend analysis, peak hour detection, and revenue forecasting
"""

from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
from sqlalchemy import func, and_, extract
from sqlalchemy.orm import Session
import numpy as np
from collections import defaultdict

from src.db.models import VehicleLog, ToggleMode, Vehicle
from config.settings import PARKING_HOURLY_RATE


class AnalyticsEngine:
    """Core analytics engine for ANPR system"""
    
    def __init__(self, db_session: Session):
        self.session = db_session
    
    # ===== Trend Analysis =====
    
    def get_daily_trends(self, start_date: datetime, end_date: datetime) -> Dict:
        """Get daily entry/exit trends"""
        results = self.session.query(
            func.date(VehicleLog.captured_at).label('date'),
            VehicleLog.toggle_mode,
            func.count(VehicleLog.log_id).label('count')
        ).filter(
            and_(
                VehicleLog.captured_at >= start_date,
                VehicleLog.captured_at <= end_date
            )
        ).group_by(
            func.date(VehicleLog.captured_at),
            VehicleLog.toggle_mode
        ).order_by('date').all()
        
        # Organize data by date
        trends = defaultdict(lambda: {'entries': 0, 'exits': 0, 'date': None})
        for date, mode, count in results:
            # func.date() returns string in SQLite, not datetime
            date_str = date if isinstance(date, str) else date.strftime('%Y-%m-%d')
            trends[date_str]['date'] = date_str
            if mode == ToggleMode.ENTRY:
                trends[date_str]['entries'] = count
            else:
                trends[date_str]['exits'] = count
        
        return dict(trends)
    
    def get_weekly_trends(self, weeks: int = 4) -> Dict:
        """Get weekly trends for the past N weeks"""
        end_date = datetime.now()
        start_date = end_date - timedelta(weeks=weeks)
        
        results = self.session.query(
            func.strftime('%Y-%W', VehicleLog.captured_at).label('week'),
            VehicleLog.toggle_mode,
            func.count(VehicleLog.log_id).label('count')
        ).filter(
            VehicleLog.captured_at >= start_date
        ).group_by(
            'week',
            VehicleLog.toggle_mode
        ).order_by('week').all()
        
        trends = defaultdict(lambda: {'entries': 0, 'exits': 0})
        for week, mode, count in results:
            if mode == ToggleMode.ENTRY:
                trends[week]['entries'] = count
            else:
                trends[week]['exits'] = count
        
        return dict(trends)
    
    def get_monthly_trends(self, months: int = 12) -> Dict:
        """Get monthly trends for the past N months"""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=months * 30)
        
        results = self.session.query(
            func.strftime('%Y-%m', VehicleLog.captured_at).label('month'),
            VehicleLog.toggle_mode,
            func.count(VehicleLog.log_id).label('count')
        ).filter(
            VehicleLog.captured_at >= start_date
        ).group_by(
            'month',
            VehicleLog.toggle_mode
        ).order_by('month').all()
        
        trends = defaultdict(lambda: {'entries': 0, 'exits': 0})
        for month, mode, count in results:
            if mode == ToggleMode.ENTRY:
                trends[month]['entries'] = count
            else:
                trends[month]['exits'] = count
        
        return dict(trends)
    
    # ===== Peak Hour Detection =====
    
    def get_peak_hours(self, date: Optional[datetime] = None) -> Dict:
        """Detect peak hours for a specific date or overall"""
        query = self.session.query(
            extract('hour', VehicleLog.captured_at).label('hour'),
            VehicleLog.toggle_mode,
            func.count(VehicleLog.log_id).label('count')
        )
        
        if date:
            query = query.filter(
                func.date(VehicleLog.captured_at) == date.date()
            )
        
        results = query.group_by('hour', VehicleLog.toggle_mode).all()
        
        hourly_data = defaultdict(lambda: {'entries': 0, 'exits': 0, 'total': 0})
        for hour, mode, count in results:
            hour_int = int(hour)
            if mode == ToggleMode.ENTRY:
                hourly_data[hour_int]['entries'] = count
            else:
                hourly_data[hour_int]['exits'] = count
            hourly_data[hour_int]['total'] += count
        
        # Find peak hours
        sorted_hours = sorted(hourly_data.items(), key=lambda x: x[1]['total'], reverse=True)
        peak_hours = sorted_hours[:3] if len(sorted_hours) >= 3 else sorted_hours
        
        return {
            'hourly_data': dict(hourly_data),
            'peak_hours': [{'hour': h, 'data': d} for h, d in peak_hours]
        }
    
    def get_peak_days(self, weeks: int = 4) -> Dict:
        """Detect peak days of the week"""
        end_date = datetime.now()
        start_date = end_date - timedelta(weeks=weeks)
        
        results = self.session.query(
            func.strftime('%w', VehicleLog.captured_at).label('day_of_week'),
            func.count(VehicleLog.log_id).label('count')
        ).filter(
            VehicleLog.captured_at >= start_date
        ).group_by('day_of_week').all()
        
        day_names = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
        daily_data = {}
        for day_num, count in results:
            day_idx = int(day_num)
            daily_data[day_names[day_idx]] = count
        
        # Find peak day
        peak_day = max(daily_data.items(), key=lambda x: x[1]) if daily_data else ('N/A', 0)
        
        return {
            'daily_data': daily_data,
            'peak_day': {'day': peak_day[0], 'count': peak_day[1]}
        }
    
    # ===== Revenue Analysis =====
    
    def get_revenue_summary(self, start_date: datetime, end_date: datetime) -> Dict:
        """Get revenue summary for a date range"""
        results = self.session.query(
            func.count(VehicleLog.log_id).label('total_exits'),
            func.sum(VehicleLog.amount).label('total_revenue'),
            func.avg(VehicleLog.amount).label('avg_revenue'),
            func.max(VehicleLog.amount).label('max_revenue'),
            func.min(VehicleLog.amount).label('min_revenue'),
            func.sum(VehicleLog.duration_hours).label('total_hours')
        ).filter(
            and_(
                VehicleLog.toggle_mode == ToggleMode.EXIT,
                VehicleLog.captured_at >= start_date,
                VehicleLog.captured_at <= end_date,
                VehicleLog.amount.isnot(None)
            )
        ).first()
        
        return {
            'total_exits': results.total_exits or 0,
            'total_revenue': round(results.total_revenue or 0, 2),
            'avg_revenue': round(results.avg_revenue or 0, 2),
            'max_revenue': round(results.max_revenue or 0, 2),
            'min_revenue': round(results.min_revenue or 0, 2) if results.min_revenue else 0,
            'total_hours': round(results.total_hours or 0, 2)
        }
    
    def get_daily_revenue(self, start_date: datetime, end_date: datetime) -> Dict:
        """Get daily revenue breakdown"""
        results = self.session.query(
            func.date(VehicleLog.captured_at).label('date'),
            func.count(VehicleLog.log_id).label('exits'),
            func.sum(VehicleLog.amount).label('revenue')
        ).filter(
            and_(
                VehicleLog.toggle_mode == ToggleMode.EXIT,
                VehicleLog.captured_at >= start_date,
                VehicleLog.captured_at <= end_date,
                VehicleLog.amount.isnot(None)
            )
        ).group_by(func.date(VehicleLog.captured_at)).order_by('date').all()
        
        daily_revenue = {}
        for date, exits, revenue in results:
            # func.date() returns string in SQLite, not datetime
            date_str = date if isinstance(date, str) else date.strftime('%Y-%m-%d')
            daily_revenue[date_str] = {
                'date': date_str,
                'exits': exits,
                'revenue': round(revenue or 0, 2)
            }
        
        return daily_revenue
    
    # ===== Vehicle Type Distribution =====
    
    def get_vehicle_type_distribution(self, start_date: datetime, end_date: datetime) -> Dict:
        """Get distribution of vehicle types"""
        results = self.session.query(
            Vehicle.vehicle_type,
            func.count(VehicleLog.log_id).label('count')
        ).join(
            VehicleLog, Vehicle.vehicle_id == VehicleLog.vehicle_id
        ).filter(
            and_(
                VehicleLog.captured_at >= start_date,
                VehicleLog.captured_at <= end_date
            )
        ).group_by(Vehicle.vehicle_type).all()
        
        distribution = {}
        total = 0
        for vehicle_type, count in results:
            vtype = vehicle_type or 'Unknown'
            distribution[vtype] = count
            total += count
        
        # Calculate percentages
        percentages = {}
        for vtype, count in distribution.items():
            percentages[vtype] = {
                'count': count,
                'percentage': round((count / total * 100) if total > 0 else 0, 2)
            }
        
        return percentages
    
    # ===== Predictive Analytics =====
    
    def forecast_parking_demand(self, days_ahead: int = 7) -> Dict:
        """Forecast parking demand for the next N days using simple moving average"""
        # Get historical data for the past 30 days
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)
        
        daily_data = self.get_daily_trends(start_date, end_date)
        
        if not daily_data:
            return {'forecast': [], 'confidence': 'low'}
        
        # Extract entry counts
        dates = sorted(daily_data.keys())
        entries = [daily_data[d]['entries'] for d in dates]
        
        if len(entries) < 7:
            return {'forecast': [], 'confidence': 'low'}
        
        # Simple moving average forecast
        window_size = min(7, len(entries))
        forecasts = []
        
        for i in range(days_ahead):
            # Use last window_size days for prediction
            recent_data = entries[-(window_size):]
            forecast_value = int(np.mean(recent_data))
            
            forecast_date = end_date + timedelta(days=i+1)
            forecasts.append({
                'date': forecast_date.strftime('%Y-%m-%d'),
                'predicted_entries': forecast_value,
                'confidence': 'medium' if len(entries) >= 14 else 'low'
            })
            
            # Add forecast to entries for next iteration
            entries.append(forecast_value)
        
        return {
            'forecast': forecasts,
            'method': 'moving_average',
            'historical_days': len(dates)
        }
    
    def forecast_revenue(self, days_ahead: int = 7) -> Dict:
        """Forecast revenue for the next N days"""
        # Get historical revenue data
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)
        
        daily_revenue = self.get_daily_revenue(start_date, end_date)
        
        if not daily_revenue:
            return {'forecast': [], 'confidence': 'low'}
        
        # Extract revenue values
        dates = sorted(daily_revenue.keys())
        revenues = [daily_revenue[d]['revenue'] for d in dates]
        
        if len(revenues) < 7:
            return {'forecast': [], 'confidence': 'low'}
        
        # Simple moving average forecast
        window_size = min(7, len(revenues))
        forecasts = []
        
        for i in range(days_ahead):
            recent_data = revenues[-(window_size):]
            forecast_value = round(np.mean(recent_data), 2)
            
            forecast_date = end_date + timedelta(days=i+1)
            forecasts.append({
                'date': forecast_date.strftime('%Y-%m-%d'),
                'predicted_revenue': forecast_value,
                'confidence': 'medium' if len(revenues) >= 14 else 'low'
            })
            
            revenues.append(forecast_value)
        
        return {
            'forecast': forecasts,
            'method': 'moving_average',
            'historical_days': len(dates)
        }
    
    def identify_patterns(self, weeks: int = 4) -> Dict:
        """Identify usage patterns and anomalies"""
        end_date = datetime.now()
        start_date = end_date - timedelta(weeks=weeks)
        
        # Get hourly patterns
        peak_hours = self.get_peak_hours()
        
        # Get daily patterns
        peak_days = self.get_peak_days(weeks)
        
        # Get average duration
        avg_duration = self.session.query(
            func.avg(VehicleLog.duration_hours)
        ).filter(
            and_(
                VehicleLog.toggle_mode == ToggleMode.EXIT,
                VehicleLog.captured_at >= start_date,
                VehicleLog.duration_hours.isnot(None)
            )
        ).scalar()
        
        # Get occupancy rate (entries without exits)
        total_entries = self.session.query(func.count(VehicleLog.log_id)).filter(
            and_(
                VehicleLog.toggle_mode == ToggleMode.ENTRY,
                VehicleLog.captured_at >= start_date
            )
        ).scalar()
        
        total_exits = self.session.query(func.count(VehicleLog.log_id)).filter(
            and_(
                VehicleLog.toggle_mode == ToggleMode.EXIT,
                VehicleLog.captured_at >= start_date
            )
        ).scalar()
        
        return {
            'peak_hours': peak_hours['peak_hours'],
            'peak_day': peak_days['peak_day'],
            'avg_duration_hours': round(avg_duration or 0, 2),
            'total_entries': total_entries or 0,
            'total_exits': total_exits or 0,
            'current_occupancy': (total_entries or 0) - (total_exits or 0),
            'exit_rate': round((total_exits / total_entries * 100) if total_entries > 0 else 0, 2)
        }
    
    # ===== Summary Statistics =====
    
    def get_summary_stats(self, period: str = 'today') -> Dict:
        """Get summary statistics for a period (today, week, month)"""
        now = datetime.now()
        
        if period == 'today':
            start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
            end_date = now
        elif period == 'week':
            start_date = now - timedelta(days=7)
            end_date = now
        elif period == 'month':
            start_date = now - timedelta(days=30)
            end_date = now
        else:
            start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
            end_date = now
        
        # Get counts
        entries = self.session.query(func.count(VehicleLog.log_id)).filter(
            and_(
                VehicleLog.toggle_mode == ToggleMode.ENTRY,
                VehicleLog.captured_at >= start_date,
                VehicleLog.captured_at <= end_date
            )
        ).scalar() or 0
        
        exits = self.session.query(func.count(VehicleLog.log_id)).filter(
            and_(
                VehicleLog.toggle_mode == ToggleMode.EXIT,
                VehicleLog.captured_at >= start_date,
                VehicleLog.captured_at <= end_date
            )
        ).scalar() or 0
        
        # Get revenue
        revenue = self.session.query(func.sum(VehicleLog.amount)).filter(
            and_(
                VehicleLog.toggle_mode == ToggleMode.EXIT,
                VehicleLog.captured_at >= start_date,
                VehicleLog.captured_at <= end_date,
                VehicleLog.amount.isnot(None)
            )
        ).scalar() or 0
        
        return {
            'period': period,
            'start_date': start_date,
            'end_date': end_date,
            'total_entries': entries,
            'total_exits': exits,
            'current_occupancy': entries - exits,
            'total_revenue': round(revenue, 2)
        }
