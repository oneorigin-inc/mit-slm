"""Test RAG integration with badge generator"""
import asyncio
import sys
from app.services.badge_generator import generate_badge_metadata_async
from app.models.requests import BadgeRequest

async def test_rag_badge_generation():
    """Test badge generation with RAG examples"""

    # Sample course input
    test_request = BadgeRequest(
        course_input="""
        course 1: Composition: Writing with a Strategy Welcome to Composition: Writing with a Strategy! In this course, you will focus on three main topics: understanding purpose, context, and audience, writing strategies and techniques, and editing and revising. In addition, the first section, will offer review on core elements of the writing process, cross-cultural communication, as well as working with words and common standards and practices. Each section includes learning opportunities through readings, videos, audio, and other relevant resources. Assessment activities with feedback also provide opportunities to check your learning, practice, and show how well you understand course content. Because the course is self-paced, you may move through the material as quickly or as slowly as you need to gain proficiency in the seven competencies that will be covered in the final assessment. If you have no prior knowledge or experience, you can expect to spend 30-40 hours on the course content. This course covers the following competencies: ● Begin your course by discussing your course planning tool report with your instructor and creating your personalized course plan together. ● The learner composes constructive feedback of written texts. ● The learner constructs a written document with correct format, style, structure, and grammar. ● The learner formulates a strategy for editing and revising written text. ● The learner incorporates writing strategies and techniques for written communication. ● The learner writes with purpose for a given context and target audience.
        """,
        badge_style="",
        badge_tone="",
        criterion_style="",
        badge_level="",
        institution="",
        custom_instructions=""
    )

    print("Testing RAG-enhanced badge generation...")
    print("=" * 60)

    result = await generate_badge_metadata_async(test_request)

    print("\n RESULT:")
    print(f"Badge Name: {result.get('badge_name')}")
    print(f"\nBadge Description: {result.get('badge_description')}")
    print(f"\nCriteria: {result.get('criteria', {}).get('narrative', '')[:200]}...")

    print("\n\n Retrieved Examples Used:")
    for example in result.get('retrieved_examples', []):
        print(f"  - {example['badge_name']} (Score: {example['similarity_score']:.3f})")

    print("\nTest completed successfully!")

if __name__ == "__main__":
    asyncio.run(test_rag_badge_generation())
