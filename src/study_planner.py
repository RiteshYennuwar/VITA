from datetime import datetime, timedelta
from typing import List, Dict, Tuple
import math
import cohere
from config import COHERE_API_KEY,GENERATION_MODEL

def create_study_schedule(text_chunks: List[str], num_days: int) -> Dict[str, List[str]]:
    """
    Create a study schedule with text chunks distributed across days
    """
    chunks_per_day = math.ceil(len(text_chunks) / num_days)
    schedule = {}
    current_date = datetime.now()
    
    for day in range(num_days):
        date_str = current_date.strftime('%Y-%m-%d')
        start_idx = day * chunks_per_day
        end_idx = min((day + 1) * chunks_per_day, len(text_chunks))
        schedule[date_str] = {
            'chunks': text_chunks[start_idx:end_idx],
            'generated': False,
            'notes': None,
            'completed': False
        }
        current_date += timedelta(days=1)
    
    return schedule

def generate_notes_for_chunks(chunks: List[str], day_number: int, total_days: int, familiarity: int) -> str:
    """
    Generate study notes from text chunks using Cohere
    """
    co = cohere.Client(COHERE_API_KEY)
    
    combined_text = " ".join(chunks)
    prompt = f"""
    As an expert tutor, create comprehensive study notes from the following text. 
    This is Day {day_number} out of {total_days} of the study material. I rate my familiarity as {familiarity} out of 
    5 in this topic.
    
    Please organize the notes with:
    1.Intoduction and prerequisites to the topic based on the familiarity scale provided
    2. Key concepts and main ideas
    3. Important details and examples
    4. Summary points
    5. Review questions

    
    Text to process:
    {combined_text}
    """
    
    response = co.generate(
        model=GENERATION_MODEL,
        prompt=prompt,
        max_tokens=2000,
        temperature=0.7
    )
    
    return response.generations[0].text

def save_study_schedule(mongo_db,filename:str, user_id: str, file_id: str, schedule: Dict[str, dict], familiarity:int) -> str:
    """
    Save the study schedule to MongoDB
    """
    schedule_data = {
        'user_id': user_id,
        'file_id': file_id,
        'schedule': schedule,
        'created_at': datetime.now(),
        'title': filename,
        'familiarity': familiarity# Get the original filename
    }
    
    return str(mongo_db.study_schedules.insert_one(schedule_data).inserted_id)

def mark_day_completed(mongo_db, schedule_id: str, date: str) -> bool:
    """
    Mark a specific day as completed
    """
    try:
        mongo_db.study_schedules.update_one(
            {'_id': schedule_id},
            {'$set': {f'schedule.{date}.completed': True}}
        )
        return True
    except Exception:
        return False

def mark_day_completed(mongo_db, schedule_id: str, date: str) -> bool:
    """
    Mark a specific day as completed
    """
    try:
        mongo_db.study_schedules.update_one(
            {'_id': schedule_id},
            {'$set': {f'schedule.{date}.completed': True}}
        )
        return True
    except Exception:
        return False