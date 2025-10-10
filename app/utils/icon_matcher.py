import json
import logging
from typing import Dict, Any, List
from app.utils.similarity import calculate_batch_similarity
from app.services.text_processor import preprocess_text

logger = logging.getLogger(__name__)

# Icons data - will be populated when JSON file is available
ICONS_DATA =[
    {
      "name": "atom.png",
      "display_name": "Atom",
      "category": "science",
      "description": "Represents scientific knowledge, chemistry, physics, molecular studies, research, scientific discovery, and STEM education",
      "keywords": ["science", "chemistry", "physics", "STEM", "molecular", "research", "atomic", "nuclear"],
      "use_cases": [
        "Science achievement badges",
        "Chemistry course completion",
        "Physics excellence",
        "Research participation",
        "Lab work proficiency"
      ]
    },
    {
      "name": "binary-code.png",
      "display_name": "Binary Code",
      "category": "technology",
      "description": "Represents computer science, programming, digital literacy, coding skills, binary systems, and computational thinking",
      "keywords": ["programming", "coding", "computer science", "binary", "digital", "technology", "software"],
      "use_cases": [
        "Programming course completion",
        "Coding bootcamp achievement",
        "Computer science excellence",
        "Digital literacy milestone",
        "Software development skills"
      ]
    },
    {
      "name": "brackets.png",
      "display_name": "Code Brackets",
      "category": "technology",
      "description": "Represents coding, programming languages, software development, syntax mastery, and technical skills",
      "keywords": ["code", "programming", "development", "syntax", "HTML", "JavaScript", "coding"],
      "use_cases": [
        "Web development achievement",
        "Programming language mastery",
        "Code review excellence",
        "Syntax proficiency",
        "Developer certification"
      ]
    },
    {
      "name": "brain.png",
      "display_name": "Brain",
      "category": "cognitive",
      "description": "Represents intelligence, critical thinking, cognitive skills, neuroscience, psychology, mental agility, and learning ability",
      "keywords": ["intelligence", "thinking", "cognitive", "psychology", "neuroscience", "mental", "learning", "knowledge"],
      "use_cases": [
        "Critical thinking achievement",
        "Psychology course completion",
        "Neuroscience studies",
        "Problem-solving excellence",
        "Mental math champion"
      ]
    },
    {
      "name": "calculator.png",
      "display_name": "Calculator",
      "category": "mathematics",
      "description": "Represents mathematical skills, calculation proficiency, accounting, statistics, numerical analysis, and quantitative reasoning",
      "keywords": ["math", "calculation", "numbers", "accounting", "statistics", "arithmetic", "algebra", "finance"],
      "use_cases": [
        "Mathematics achievement",
        "Accounting certification",
        "Statistics mastery",
        "Financial literacy",
        "Arithmetic excellence"
      ]
    },
    {
      "name": "checkmark.png",
      "display_name": "Checkmark",
      "category": "achievement",
      "description": "Represents completion, success, verification, quality assurance, task accomplishment, and goal achievement",
      "keywords": ["complete", "done", "success", "verified", "achieved", "finished", "approved", "passed"],
      "use_cases": [
        "Course completion",
        "Task achievement",
        "Quality verification",
        "Test passed",
        "Requirement fulfilled"
      ]
    },
    {
      "name": "clock.png",
      "display_name": "Clock",
      "category": "skills",
      "description": "Represents time management, punctuality, deadline achievement, scheduling skills, and efficiency",
      "keywords": ["time", "management", "punctual", "deadline", "schedule", "timely", "efficient", "duration"],
      "use_cases": [
        "Time management excellence",
        "Perfect attendance",
        "Deadline achievement",
        "Punctuality award",
        "Speed completion bonus"
      ]
    },
    {
      "name": "cloud-service.png",
      "display_name": "Cloud Service",
      "category": "technology",
      "description": "Represents cloud computing, online services, digital storage, SaaS platforms, and modern IT infrastructure",
      "keywords": ["cloud", "computing", "storage", "online", "SaaS", "AWS", "Azure", "infrastructure"],
      "use_cases": [
        "Cloud computing certification",
        "AWS/Azure proficiency",
        "Online collaboration",
        "Digital transformation",
        "Cloud architecture skills"
      ]
    },
    {
      "name": "code.png",
      "display_name": "Code",
      "category": "technology",
      "description": "Represents software development, programming proficiency, coding skills, and technical expertise",
      "keywords": ["programming", "software", "development", "coding", "script", "algorithm", "function"],
      "use_cases": [
        "Software engineering achievement",
        "Algorithm mastery",
        "Code quality excellence",
        "Programming contest winner",
        "Technical skills certification"
      ]
    },
    {
      "name": "color-palette.png",
      "display_name": "Color Palette",
      "category": "creative",
      "description": "Represents artistic skills, design thinking, creativity, visual arts, color theory, and aesthetic sense",
      "keywords": ["art", "design", "creative", "colors", "painting", "visual", "aesthetic", "graphics"],
      "use_cases": [
        "Art class achievement",
        "Design course completion",
        "Creative excellence",
        "Visual arts mastery",
        "Graphic design certification"
      ]
    },
    {
      "name": "crown.png",
      "display_name": "Crown",
      "category": "achievement",
      "description": "Represents leadership, excellence, top performance, mastery, championship, and highest achievement",
      "keywords": ["leader", "champion", "winner", "best", "top", "excellence", "master", "king", "queen"],
      "use_cases": [
        "Class valedictorian",
        "Competition champion",
        "Leadership excellence",
        "Top performer",
        "Master level achievement"
      ]
    },
    {
      "name": "diamond.png",
      "display_name": "Diamond",
      "category": "achievement",
      "description": "Represents premium quality, rare achievement, exceptional performance, valuable skills, and brilliance",
      "keywords": ["premium", "quality", "rare", "valuable", "exceptional", "brilliant", "precious", "elite"],
      "use_cases": [
        "Premium certification",
        "Exceptional achievement",
        "Elite performance",
        "Rare skill mastery",
        "Diamond tier reached"
      ]
    },
    {
      "name": "dna.png",
      "display_name": "DNA",
      "category": "science",
      "description": "Represents biology, genetics, life sciences, biotechnology, medical research, and biological studies",
      "keywords": ["biology", "genetics", "DNA", "life science", "biotechnology", "medical", "research", "genome"],
      "use_cases": [
        "Biology achievement",
        "Genetics course completion",
        "Biotechnology certification",
        "Medical studies excellence",
        "Life science research"
      ]
    },
    {
      "name": "energy.png",
      "display_name": "Energy",
      "category": "science",
      "description": "Represents physics, renewable energy, sustainability, power systems, enthusiasm, and dynamic performance",
      "keywords": ["energy", "power", "physics", "renewable", "sustainability", "electric", "dynamic", "vigor"],
      "use_cases": [
        "Physics achievement",
        "Renewable energy studies",
        "Sustainability project",
        "High energy performance",
        "Environmental science"
      ]
    },
    {
      "name": "gear.png",
      "display_name": "Gear",
      "category": "engineering",
      "description": "Represents engineering, mechanical skills, technical configuration, systems thinking, and process optimization",
      "keywords": ["engineering", "mechanical", "settings", "technical", "machinery", "process", "system", "configuration"],
      "use_cases": [
        "Engineering excellence",
        "Mechanical skills certification",
        "Technical proficiency",
        "Process improvement",
        "System optimization"
      ]
    },
    {
      "name": "gem.png",
      "display_name": "Gem",
      "category": "achievement",
      "description": "Represents precious achievement, special recognition, unique skills, and valuable contribution",
      "keywords": ["precious", "special", "unique", "valuable", "rare", "jewel", "treasure", "exceptional"],
      "use_cases": [
        "Special recognition",
        "Unique achievement",
        "Valuable contribution",
        "Hidden talent discovery",
        "Exceptional skill"
      ]
    },
    {
      "name": "globe.png",
      "display_name": "Globe",
      "category": "geography",
      "description": "Represents global awareness, geography, international studies, world languages, cultural diversity, and environmental studies",
      "keywords": ["global", "world", "geography", "international", "earth", "culture", "diversity", "environment"],
      "use_cases": [
        "Geography excellence",
        "Global studies completion",
        "Language learning achievement",
        "Cultural awareness",
        "International collaboration"
      ]
    },
    {
      "name": "goal.png",
      "display_name": "Goal",
      "category": "achievement",
      "description": "Represents goal achievement, target completion, objective success, milestone reached, and purposeful accomplishment",
      "keywords": ["goal", "target", "objective", "achievement", "milestone", "purpose", "aim", "success"],
      "use_cases": [
        "Goal achievement",
        "Milestone reached",
        "Target exceeded",
        "Objective completed",
        "Personal best"
      ]
    },
    {
      "name": "graduation-cap.png",
      "display_name": "Graduation Cap",
      "category": "academic",
      "description": "Represents academic achievement, graduation, education completion, scholarly success, and learning accomplishment",
      "keywords": ["graduation", "academic", "education", "degree", "diploma", "university", "college", "scholar"],
      "use_cases": [
        "Course graduation",
        "Degree completion",
        "Academic excellence",
        "Education milestone",
        "Certification achieved"
      ]
    },
    {
      "name": "growth.png",
      "display_name": "Growth",
      "category": "progress",
      "description": "Represents personal development, progress, improvement, skill advancement, and continuous learning",
      "keywords": ["growth", "progress", "improvement", "development", "advance", "evolve", "increase", "expand"],
      "use_cases": [
        "Personal development",
        "Skill improvement",
        "Progress milestone",
        "Growth mindset achievement",
        "Continuous improvement"
      ]
    },
    {
      "name": "handshake.png",
      "display_name": "Handshake",
      "category": "collaboration",
      "description": "Represents collaboration, teamwork, partnership, agreement, cooperation, and professional networking",
      "keywords": ["collaboration", "teamwork", "partnership", "cooperation", "agreement", "networking", "deal", "alliance"],
      "use_cases": [
        "Team collaboration excellence",
        "Partnership achievement",
        "Networking success",
        "Cooperation award",
        "Peer mentoring"
      ]
    },
    {
      "name": "ink-bottle.png",
      "display_name": "Ink Bottle",
      "category": "creative",
      "description": "Represents writing skills, creative writing, literature, poetry, journalism, and traditional arts",
      "keywords": ["writing", "literature", "poetry", "creative", "author", "journalism", "essay", "composition"],
      "use_cases": [
        "Creative writing excellence",
        "Literature achievement",
        "Poetry competition",
        "Essay writing award",
        "Journalism skills"
      ]
    },
    {
      "name": "leadership.png",
      "display_name": "Leadership",
      "category": "skills",
      "description": "Represents leadership qualities, management skills, team guidance, decision making, and organizational abilities",
      "keywords": ["leader", "management", "guide", "direct", "organize", "command", "influence", "inspire"],
      "use_cases": [
        "Leadership program completion",
        "Team leader certification",
        "Management training",
        "Student council achievement",
        "Project leadership"
      ]
    },
    {
      "name": "medal.png",
      "display_name": "Medal",
      "category": "achievement",
      "description": "Represents recognition, award, honor, competitive achievement, and distinguished performance",
      "keywords": ["medal", "award", "honor", "recognition", "prize", "achievement", "competition", "distinction"],
      "use_cases": [
        "Competition medal",
        "Honor roll achievement",
        "Distinguished performance",
        "Academic medal",
        "Sports achievement"
      ]
    },
    {
      "name": "microscope.png",
      "display_name": "Microscope",
      "category": "science",
      "description": "Represents scientific research, laboratory skills, biology, detailed analysis, and investigative learning",
      "keywords": ["research", "laboratory", "biology", "analysis", "investigation", "microscopy", "study", "chemistry"],
      "use_cases": [
        "Lab skills certification",
        "Research project completion",
        "Biology excellence",
        "Scientific investigation",
        "Laboratory safety"
      ]
    },
    {
      "name": "music_note.png",
      "display_name": "Music Note",
      "category": "creative",
      "description": "Represents musical talent, music theory, performance arts, rhythm, composition, and audio production",
      "keywords": ["music", "note", "melody", "rhythm", "composition", "performance", "audio", "song"],
      "use_cases": [
        "Music theory completion",
        "Performance excellence",
        "Composition achievement",
        "Instrument mastery",
        "Choir participation"
      ]
    },
    {
      "name": "presentation.png",
      "display_name": "Presentation",
      "category": "communication",
      "description": "Represents presentation skills, public speaking, communication excellence, teaching ability, and information sharing",
      "keywords": ["presentation", "speaking", "communication", "teaching", "lecture", "seminar", "pitch", "demonstration"],
      "use_cases": [
        "Presentation excellence",
        "Public speaking achievement",
        "Teaching assistant",
        "Seminar completion",
        "Demo day winner"
      ]
    },
    {
      "name": "robot.png",
      "display_name": "Robot",
      "category": "technology",
      "description": "Represents robotics, artificial intelligence, automation, STEM education, and technological innovation",
      "keywords": ["robot", "AI", "automation", "robotics", "technology", "innovation", "machine", "artificial"],
      "use_cases": [
        "Robotics club achievement",
        "AI course completion",
        "Automation project",
        "STEM excellence",
        "Innovation award"
      ]
    },
    {
      "name": "shield.png",
      "display_name": "Shield",
      "category": "security",
      "description": "Represents security, protection, cybersecurity, safety, defense, reliability, and trustworthiness",
      "keywords": ["security", "protection", "safety", "defense", "cybersecurity", "guard", "secure", "trust"],
      "use_cases": [
        "Cybersecurity certification",
        "Safety training completion",
        "Security excellence",
        "Data protection skills",
        "Ethical hacking"
      ]
    },
    {
      "name": "solution.png",
      "display_name": "Solution",
      "category": "problem-solving",
      "description": "Represents problem-solving, solution finding, analytical thinking, innovation, and creative resolution",
      "keywords": ["solution", "solve", "answer", "resolve", "fix", "innovation", "breakthrough", "discovery"],
      "use_cases": [
        "Problem-solving excellence",
        "Innovation challenge winner",
        "Solution architect",
        "Debugging champion",
        "Case study completion"
      ]
    },
    {
      "name": "emotions.png",
      "display_name": "Emotions",
      "category": "social-emotional",
      "description": "Represents emotional intelligence, empathy, self-awareness, interpersonal skills, and emotional regulation",
      "keywords": ["emotions", "feelings", "empathy", "emotional", "awareness", "mindfulness", "compassion", "understanding"],
      "use_cases": [
        "Emotional intelligence mastery",
        "Empathy leadership",
        "Mental health awareness",
        "Peer support excellence",
        "Mindfulness practice completion"
      ]
    },
    {
      "name": "spaceship.png",
      "display_name": "Spaceship",
      "category": "innovation",
      "description": "Represents space science, aerospace, exploration, innovation, ambitious goals, and futuristic thinking",
      "keywords": ["space", "rocket", "aerospace", "exploration", "innovation", "astronomy", "future", "launch"],
      "use_cases": [
        "Space science achievement",
        "Innovation project",
        "Aerospace studies",
        "Ambitious goal reached",
        "STEM exploration"
      ]
    },
    {
      "name": "speech_bubble.png",
      "display_name": "Speech Bubble",
      "category": "communication",
      "description": "Represents communication skills, dialogue, discussion, feedback, conversation, and social interaction",
      "keywords": ["communication", "dialogue", "discussion", "chat", "conversation", "feedback", "talk", "message"],
      "use_cases": [
        "Communication skills",
        "Debate team achievement",
        "Peer feedback excellence",
        "Discussion forum leader",
        "Language proficiency"
      ]
    },
    {
      "name": "star.png",
      "display_name": "Star",
      "category": "achievement",
      "description": "Represents excellence, outstanding performance, favorite status, quality, and special recognition",
      "keywords": ["star", "excellence", "outstanding", "favorite", "quality", "special", "top", "best"],
      "use_cases": [
        "Star student",
        "Outstanding performance",
        "Excellence award",
        "Top rating achieved",
        "Special recognition"
      ]
    },
    {
      "name": "teamwork.png",
      "display_name": "Teamwork",
      "category": "collaboration",
      "description": "Represents team collaboration, group work, cooperative learning, collective achievement, and synergy",
      "keywords": ["team", "collaboration", "group", "together", "cooperative", "collective", "unity", "synergy"],
      "use_cases": [
        "Team project excellence",
        "Group collaboration",
        "Cooperative learning",
        "Team building participation",
        "Collective achievement"
      ]
    },
    {
      "name": "thumbs-up.png",
      "display_name": "Thumbs Up",
      "category": "feedback",
      "description": "Represents approval, positive feedback, encouragement, good job recognition, and satisfaction",
      "keywords": ["approval", "positive", "good", "like", "agree", "encourage", "satisfied", "yes"],
      "use_cases": [
        "Positive peer review",
        "Good behavior award",
        "Encouragement badge",
        "Satisfaction achievement",
        "Approval earned"
      ]
    },
    {
      "name": "trophy.png",
      "display_name": "Trophy",
      "category": "achievement",
      "description": "Represents victory, championship, first place, competition winner, and ultimate achievement",
      "keywords": ["trophy", "winner", "champion", "victory", "first", "competition", "prize", "tournament"],
      "use_cases": [
        "Competition winner",
        "Championship trophy",
        "First place achievement",
        "Tournament victor",
        "Grand prize winner"
      ]
    },
    {
  "name": "art.png",
  "display_name": "Arts & Culture",
  "category": "creative-arts",
  "description": "Represents artistic expression, performing arts, visual arts, music, dance, theater, and cultural activities",
  "keywords": [
    "art",
    "artist",
    "creative",
    "acting",
    "theater",
    "performance",
    "singing",
    "music",
    "dancing",
    "dance",
    "cultural",
    "culture",
    "drama",
    "painting",
    "drawing",
    "sculpture",
    "exhibition",
    "concert",
    "recital",
    "stage",
    "creative expression"
  ],
  "use_cases": [
    "Art competition winner",
    "Theater/drama performance excellence",
    "Music recital or singing achievement",
    "Dance performance recognition",
    "Cultural event participation",
    "Creative showcase winner",
    "Arts festival achievement",
    "Gallery exhibition artist",
    "Performing arts excellence"
  ]
},
]


# Complete icon keywords fallback for all 36 icons
ICON_KEYWORDS = {
    "atom.png": ["science", "chemistry", "physics", "STEM", "molecular", "research", "atomic", "nuclear", "lab"],
    "binary-code.png": ["programming", "coding", "computer", "binary", "digital", "technology", "software", "data"],
    "brackets.png": ["code", "programming", "development", "syntax", "HTML", "JavaScript", "web", "developer"],
    "brain.png": ["intelligence", "thinking", "cognitive", "psychology", "neuroscience", "mental", "learning", "knowledge"],
    "calculator.png": ["math", "calculation", "numbers", "accounting", "statistics", "arithmetic", "algebra", "finance"],
    "checkmark.png": ["complete", "done", "success", "verified", "achieved", "finished", "approved", "passed"],
    "clock.png": ["time", "management", "punctual", "deadline", "schedule", "timely", "efficient", "duration"],
    "cloud-service.png": ["cloud", "computing", "storage", "online", "SaaS", "AWS", "Azure", "infrastructure"],
    "code.png": ["programming", "software", "development", "coding", "script", "algorithm", "function", "engineer"],
    "color-palette.png": ["art", "design", "creative", "colors", "painting", "visual", "aesthetic", "graphics"],
    "crown.png": ["leader", "champion", "winner", "best", "top", "excellence", "master", "first"],
    "diamond.png": ["premium", "quality", "rare", "valuable", "exceptional", "brilliant", "precious", "elite"],
    "dna.png": ["biology", "genetics", "DNA", "life", "biotechnology", "medical", "research", "genome"],
    "energy.png": ["energy", "power", "physics", "renewable", "sustainability", "electric", "dynamic", "vigor"],
    "gear.png": ["engineering", "mechanical", "settings", "technical", "machinery", "process", "system", "configuration"],
    "gem.png": ["precious", "special", "unique", "valuable", "rare", "jewel", "treasure", "exceptional"],
    "globe.png": ["global", "world", "geography", "international", "earth", "culture", "diversity", "environment"],
    "goal.png": ["goal", "target", "objective", "achievement", "milestone", "purpose", "aim", "success"],
    "graduation-cap.png": ["graduation", "academic", "education", "degree", "diploma", "university", "college", "scholar"],
    "growth.png": ["growth", "progress", "improvement", "development", "advance", "evolve", "increase", "expand"],
    "handshake.png": ["collaboration", "teamwork", "partnership", "cooperation", "agreement", "networking", "deal", "alliance"],
    "ink-bottle.png": ["writing", "literature", "poetry", "creative", "author", "journalism", "essay", "composition"],
    "leadership.png": ["leader", "management", "guide", "direct", "organize", "command", "influence", "inspire"],
    "medal.png": ["medal", "award", "honor", "recognition", "prize", "achievement", "competition", "distinction"],
    "microscope.png": ["research", "laboratory", "biology", "analysis", "investigation", "microscopy", "study", "chemistry"],
    "music_note.png": ["music", "note", "melody", "rhythm", "composition", "performance", "audio", "song"],
    "presentation.png": ["presentation", "speaking", "communication", "teaching", "lecture", "seminar", "pitch", "demonstration"],
    "robot.png": ["robot", "AI", "automation", "robotics", "technology", "innovation", "machine", "artificial"],
    "shield.png": ["security", "protection", "safety", "defense", "cybersecurity", "guard", "secure", "trust"],
    "solution.png": ["solution", "solve", "answer", "resolve", "fix", "innovation", "breakthrough", "discovery"],
    "spaceship.png": ["space", "rocket", "aerospace", "exploration", "innovation", "astronomy", "future", "launch"],
    "speech_bubble.png": ["communication", "dialogue", "discussion", "chat", "conversation", "feedback", "talk", "message"],
    "star.png": ["star", "excellence", "outstanding", "favorite", "quality", "special", "top", "best"],
    "teamwork.png": ["team", "collaboration", "group", "together", "cooperative", "collective", "unity", "synergy"],
    "thumbs-up.png": ["approval", "positive", "good", "like", "agree", "encourage", "satisfied", "yes"],
    "trophy.png": ["trophy", "winner", "champion", "victory", "first", "competition", "prize", "tournament"]
}

def load_icons_data(json_file_path: str):
    """Load icons data from JSON file"""
    global ICONS_DATA
    try:
        with open(json_file_path, 'r', encoding='utf-8') as f:
            ICONS_DATA = json.load(f)
        
        # Validate icons have required fields
        valid_icons = [
            icon for icon in ICONS_DATA 
            if icon.get('name') and (
                icon.get('description') or 
                icon.get('keywords') or 
                icon.get('use_cases')
            )
        ]
        
        if len(valid_icons) < len(ICONS_DATA):
            logger.warning(
                f"Only {len(valid_icons)}/{len(ICONS_DATA)} icons have valid data. "
                f"Some icons may be missing required fields."
            )
        
        ICONS_DATA = valid_icons
        logger.info(f"✓ Loaded {len(ICONS_DATA)} valid icons from {json_file_path}")
        
    except FileNotFoundError:
        logger.warning(f"⚠ Icons file not found: {json_file_path}, using built-in fallback data")
        ICONS_DATA = []
    except json.JSONDecodeError as e:
        logger.error(f"⚠ Invalid JSON in icons file: {e}, using built-in fallback data")
        ICONS_DATA = []
    except Exception as e:
        logger.error(f"⚠ Error loading icons: {e}, using built-in fallback data")
        ICONS_DATA = []


async def get_icon_suggestions_for_badge(
    badge_name: str,
    badge_description: str,
    custom_instructions: str = "",
    top_k: int = 3
) -> Dict[str, Any]:
    """
    Get icon suggestions using TF-IDF similarity matching.
    
    Args:
        badge_name: Name of the badge
        badge_description: Description of the badge
        custom_instructions: Additional context for matching
        top_k: Number of alternative suggestions to return
        
    Returns:
        Dictionary with suggested icon, alternatives, and metadata
    """
    from app.services.text_processor import preprocess_text
    from app.utils.similarity import calculate_batch_similarity
    
    # Combine all text for matching
    combined_text = f"{badge_name} {badge_description} {custom_instructions}"
    
    # Use TF-IDF similarity if icons data is available
    if ICONS_DATA and len(ICONS_DATA) > 0:
        processed_query = preprocess_text(combined_text)
        
        if not processed_query:
            logger.warning(f"Empty query after preprocessing for badge: {badge_name}")
            return _get_fallback_response(badge_name, badge_description, top_k)
        
        # Prepare icon texts for comparison
        icon_texts = []
        for icon in ICONS_DATA:
            # Combine all icon metadata
            icon_keywords = ' '.join(icon.get('keywords', []))
            icon_use_cases = ' '.join(icon.get('use_cases', []))
            icon_description = icon.get('description', '')
            
            # Build comprehensive icon text
            icon_text = f"{icon_description} {icon_keywords} {icon_use_cases}".strip()
            
            # Preprocess for consistency
            processed_icon_text = preprocess_text(icon_text)
            icon_texts.append(processed_icon_text)
        
        # Calculate similarities for all icons at once
        similarity_scores = calculate_batch_similarity(processed_query, icon_texts)
        
        # Build results with scores
        similarities = []
        for idx, icon in enumerate(ICONS_DATA):
            score = float(similarity_scores[idx])
            similarities.append({
                "name": icon["name"],
                "display_name": icon.get("display_name", icon["name"]),
                "description": icon.get("description", ""),
                "category": icon.get("category", ""),
                "keywords": icon.get("keywords", []),
                "similarity_score": round(score, 4)
            })
        
        # Sort by similarity score (descending)
        similarities.sort(key=lambda x: x["similarity_score"], reverse=True)
        
        # Get top result and alternatives
        top_icon = similarities[0] if similarities else None
        alternatives = similarities[1:top_k] if len(similarities) > 1 else []
        
        # Log top matches for monitoring
        if top_icon:
            logger.info(
                f"Icon match for '{badge_name}': {top_icon['name']} "
                f"(score: {top_icon['similarity_score']:.4f})"
            )
        
        # Use smart fallback if similarity is too low
        if not top_icon or top_icon["similarity_score"] < 0.15:
            logger.warning(
                f"Low similarity score ({top_icon['similarity_score']:.4f} < 0.15) "
                f"for badge: {badge_name}. Using smart fallback."
            )
            return _get_smart_fallback_response(
                badge_name, 
                badge_description, 
                alternatives[:top_k-1]
            )
        
        return {
            "suggested_icon": top_icon,
            "alternatives": alternatives,
            "matching_method": "tfidf_batch_similarity",
            "total_icons_available": len(ICONS_DATA),
            "query_processed": processed_query[:100]
        }
    
    else:
        # Fallback to keyword matching if no icons data
        logger.info(f"No icons data available. Using keyword fallback for: {badge_name}")
        return _get_keyword_fallback_response(badge_name, badge_description, combined_text, top_k)

def _get_keyword_fallback_response(
    badge_name: str,
    badge_description: str,
    combined_text: str,
    top_k: int
) -> Dict[str, Any]:
    """Fallback to simple keyword matching when icons data is unavailable"""
    combined_text_lower = combined_text.lower()
    
    # Score icons based on keyword matches
    scores = {}
    for icon, keywords in ICON_KEYWORDS.items():
        score = sum(1 for keyword in keywords if keyword.lower() in combined_text_lower)
        if score > 0:
            scores[icon] = score
    
    sorted_icons = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    
    if sorted_icons:
        suggested = sorted_icons[0][0]
        normalized_score = min(sorted_icons[0][1] / 8.0, 1.0)
        alternatives = [
            {
                "name": icon,
                "display_name": icon.replace('.png', '').replace('-', ' ').title(),
                "similarity_score": round(min(score / 8.0, 1.0), 4)
            }
            for icon, score in sorted_icons[1:top_k]
        ]
    else:
        # No keyword matches - use smart fallback
        logger.warning(f"No keyword matches for badge: {badge_name}")
        return _get_smart_fallback_response(badge_name, badge_description, [])
    
    return {
        "suggested_icon": {
            "name": suggested,
            "display_name": suggested.replace('.png', '').replace('-', ' ').title(),
            "description": f"Keyword-matched icon for {badge_name}",
            "category": "achievement",
            "similarity_score": round(normalized_score, 4)
        },
        "alternatives": alternatives,
        "matching_method": "keyword_fallback",
        "total_icons_available": len(ICON_KEYWORDS)
    }


def _get_smart_fallback_response(
    badge_name: str,
    badge_description: str,
    alternatives: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Smart fallback that tries to match based on content categories.
    Used when similarity scores are too low or no data available.
    """
    combined_text = f"{badge_name} {badge_description}".lower()
    
    # Category-based matching
    if any(word in combined_text for word in ['chemistry', 'chemical', 'molecule', 'atom', 'lab']):
        icon = {"name": "atom.png", "display_name": "Atom", "category": "science"}
    elif any(word in combined_text for word in ['code', 'coding', 'programming', 'software', 'developer', 'binary']):
        icon = {"name": "binary-code.png", "display_name": "Binary Code", "category": "technology"}
    elif any(word in combined_text for word in ['science', 'scientific', 'research', 'experiment']):
        icon = {"name": "atom.png", "display_name": "Science", "category": "science"}
    elif any(word in combined_text for word in ['education', 'teaching', 'learning', 'teacher', 'student', 'praxis']):
        icon = {"name": "book.png", "display_name": "Education", "category": "education"}
    elif any(word in combined_text for word in ['math', 'mathematics', 'calculus', 'algebra', 'geometry']):
        icon = {"name": "calculator.png", "display_name": "Mathematics", "category": "math"}
    elif any(word in combined_text for word in ['art', 'design', 'creative', 'drawing', 'painting']):
        icon = {"name": "palette.png", "display_name": "Art", "category": "creative"}
    elif any(word in combined_text for word in ['music', 'musical', 'instrument', 'song', 'melody']):
        icon = {"name": "music-note.png", "display_name": "Music", "category": "creative"}
    elif any(word in combined_text for word in ['fitness', 'exercise', 'workout', 'health', 'sport']):
        icon = {"name": "dumbbell.png", "display_name": "Fitness", "category": "health"}
    elif any(word in combined_text for word in ['goal', 'target', 'objective', 'milestone']):
        icon = {"name": "goal.png", "display_name": "Goal", "category": "achievement"}
    elif any(word in combined_text for word in ['star', 'excellence', 'outstanding', 'exceptional']):
        icon = {"name": "star.png", "display_name": "Star", "category": "achievement"}
    else:
        # Default fallback
        icon = {"name": "trophy.png", "display_name": "Trophy", "category": "achievement"}
    
    # Complete the icon data
    icon.update({
        "description": f"Category-matched icon for {badge_name}",
        "keywords": [],
        "similarity_score": 0.5
    })
    
    logger.info(f"Smart fallback selected: {icon['name']} for badge: {badge_name}")
    
    return {
        "suggested_icon": icon,
        "alternatives": alternatives,
        "matching_method": "smart_category_fallback",
        "total_icons_available": len(ICONS_DATA) if ICONS_DATA else 0
    }


def _get_fallback_response(
    badge_name: str,
    badge_description: str,
    top_k: int
) -> Dict[str, Any]:
    """Complete fallback when everything else fails"""
    logger.error(f"Using complete fallback for badge: {badge_name}")
    
    return {
        "suggested_icon": {
            "name": "trophy.png",
            "display_name": "Trophy",
            "description": "Default achievement icon",
            "category": "achievement",
            "keywords": ["achievement", "success"],
            "similarity_score": 0.0
        },
        "alternatives": [],
        "matching_method": "emergency_fallback",
        "total_icons_available": 0,
        "error": "Icon matching failed - using default"
    }
