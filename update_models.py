from app.core.database import SessionLocal
from app.models.system_config import SystemConfig
import json

def update():
    db = SessionLocal()
    try:
        config = db.query(SystemConfig).filter(SystemConfig.config_key == 'gemini_models').first()
        if config:
            val = config.config_value
            # Put 2.5-flash at the beginning for stability
            new_models = ['gemini-2.5-flash', 'gemini-2.5-flash']
            for m in val.get('preferred_models', []):
                if m not in new_models:
                    new_models.append(m)
            val['preferred_models'] = new_models
            config.config_value = val
            db.commit()
            print(f"Updated preferred models: {new_models}")
        else:
            print("Config not found")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    update()
