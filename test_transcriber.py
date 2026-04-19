"""
Test script for WhisperTranscriber class

This script demonstrates how to use the WhisperTranscriber class
for audio transcription tasks.
"""

import sys
import logging
from pathlib import Path
from whisper_transcriber import WhisperTranscriber

# Setup logging to see detailed information
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def test_basic_transcription():
    """Test basic transcription functionality"""
    print("\n" + "="*60)
    print("TEST 1: Basic Transcription")
    print("="*60)
    
    try:
        # Initialize transcriber with base model
        print("\nInitializing transcriber...")
        transcriber = WhisperTranscriber(
            model_size="base",
            device="cpu",
            compute_type="int8"
        )
        print("✓ Transcriber initialized successfully")
        
        # Ask user for audio file path
        audio_file = input("\nEnter path to audio file (or press Enter to skip): ").strip()
        
        if not audio_file:
            print("⊘ Skipping test - no audio file provided")
            return
        
        # Check if file exists
        if not Path(audio_file).exists():
            print(f"✗ Audio file not found: {audio_file}")
            return
        
        print(f"\nTranscribing: {audio_file}")
        result = transcriber.transcribe(audio_file)
        
        print("\n" + "-"*60)
        print("TRANSCRIPTION RESULT:")
        print("-"*60)
        print(f"\nDetected Language: {result['language']}")
        print(f"Language Probability: {result['language_probability']}")
        print(f"Number of Segments: {len(result['segments'])}")
        print(f"\nTranscribed Text:\n{result['text']}")
        
        print("\n" + "-"*60)
        print("SEGMENTS WITH TIMESTAMPS:")
        print("-"*60)
        for i, segment in enumerate(result['segments'], 1):
            print(f"\n[Segment {i}]")
            print(f"  Time: {segment['start']:.2f}s - {segment['end']:.2f}s")
            print(f"  Text: {segment['text']}")
            if segment['confidence']:
                print(f"  Confidence: {segment['confidence']:.4f}")
        
        print("\n✓ Test 1 completed successfully")
        
    except FileNotFoundError as e:
        print(f"✗ Error: {e}")
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        logger.exception("Error during transcription test")


def test_language_detection():
    """Test automatic language detection"""
    print("\n" + "="*60)
    print("TEST 2: Language Detection")
    print("="*60)
    
    try:
        print("\nInitializing transcriber...")
        transcriber = WhisperTranscriber(model_size="base", device="cpu")
        
        audio_file = input("\nEnter path to audio file (or press Enter to skip): ").strip()
        
        if not audio_file:
            print("⊘ Skipping test - no audio file provided")
            return
        
        if not Path(audio_file).exists():
            print(f"✗ Audio file not found: {audio_file}")
            return
        
        print(f"\nTranscribing (auto language detection): {audio_file}")
        result = transcriber.transcribe(audio_file, language=None)
        
        print("\n" + "-"*60)
        print("LANGUAGE DETECTION RESULT:")
        print("-"*60)
        print(f"Detected Language: {result['language']}")
        print(f"Language Probability: {result['language_probability']}")
        print(f"\nTranscribed Text:\n{result['text']}")
        print("\n✓ Test 2 completed successfully")
        
    except Exception as e:
        print(f"✗ Error: {e}")
        logger.exception("Error during language detection test")


def test_get_text_only():
    """Test getting transcribed text only (without segments)"""
    print("\n" + "="*60)
    print("TEST 3: Get Text Only")
    print("="*60)
    
    try:
        print("\nInitializing transcriber...")
        transcriber = WhisperTranscriber(model_size="base", device="cpu")
        
        audio_file = input("\nEnter path to audio file (or press Enter to skip): ").strip()
        
        if not audio_file:
            print("⊘ Skipping test - no audio file provided")
            return
        
        if not Path(audio_file).exists():
            print(f"✗ Audio file not found: {audio_file}")
            return
        
        print(f"\nGetting text from: {audio_file}")
        text = transcriber.transcribe_and_get_text(audio_file)
        
        print("\n" + "-"*60)
        print("TRANSCRIBED TEXT:")
        print("-"*60)
        print(f"\n{text}")
        print("\n✓ Test 3 completed successfully")
        
    except Exception as e:
        print(f"✗ Error: {e}")
        logger.exception("Error during text-only test")


def test_with_timestamps():
    """Test getting segments with timestamps"""
    print("\n" + "="*60)
    print("TEST 4: Get Timestamps Only")
    print("="*60)
    
    try:
        print("\nInitializing transcriber...")
        transcriber = WhisperTranscriber(model_size="base", device="cpu")
        
        audio_file = input("\nEnter path to audio file (or press Enter to skip): ").strip()
        
        if not audio_file:
            print("⊘ Skipping test - no audio file provided")
            return
        
        if not Path(audio_file).exists():
            print(f"✗ Audio file not found: {audio_file}")
            return
        
        print(f"\nGetting segments from: {audio_file}")
        segments = transcriber.transcribe_with_timestamps(audio_file)
        
        print("\n" + "-"*60)
        print("SEGMENTS WITH TIMESTAMPS:")
        print("-"*60)
        for i, segment in enumerate(segments, 1):
            print(f"\n[{i}] {segment['start']:.2f}s - {segment['end']:.2f}s")
            print(f"    {segment['text']}")
        
        print(f"\n✓ Test 4 completed successfully ({len(segments)} segments)")
        
    except Exception as e:
        print(f"✗ Error: {e}")
        logger.exception("Error during timestamp test")


def test_different_model_size():
    """Test with different model sizes"""
    print("\n" + "="*60)
    print("TEST 5: Different Model Sizes")
    print("="*60)
    
    model_sizes = ["tiny", "base", "small"]
    
    print("\nAvailable model sizes (from fastest to most accurate):")
    for i, size in enumerate(model_sizes, 1):
        print(f"  {i}. {size}")
    
    try:
        choice = input("\nSelect model size (1-3) or press Enter to skip: ").strip()
        
        if not choice:
            print("⊘ Skipping test")
            return
        
        if choice not in ["1", "2", "3"]:
            print("✗ Invalid choice")
            return
        
        model_size = model_sizes[int(choice) - 1]
        
        print(f"\nInitializing transcriber with '{model_size}' model...")
        transcriber = WhisperTranscriber(
            model_size=model_size,
            device="cpu",
            compute_type="int8"
        )
        print("✓ Transcriber initialized")
        
        audio_file = input("\nEnter path to audio file (or press Enter to skip): ").strip()
        
        if not audio_file:
            print("⊘ Skipping test")
            return
        
        if not Path(audio_file).exists():
            print(f"✗ Audio file not found: {audio_file}")
            return
        
        print(f"\nTranscribing with '{model_size}' model...")
        result = transcriber.transcribe(audio_file)
        
        print("\n" + "-"*60)
        print(f"RESULT (Model: {model_size}):")
        print("-"*60)
        print(f"Language: {result['language']}")
        print(f"Text: {result['text']}")
        print("\n✓ Test 5 completed successfully")
        
    except Exception as e:
        print(f"✗ Error: {e}")
        logger.exception("Error during model size test")


def show_menu():
    """Display test menu"""
    print("\n" + "="*60)
    print("WHISPER TRANSCRIBER TEST SUITE")
    print("="*60)
    print("\nAvailable Tests:")
    print("  1. Basic Transcription")
    print("  2. Language Detection")
    print("  3. Get Text Only")
    print("  4. Get Timestamps Only")
    print("  5. Different Model Sizes")
    print("  6. Run All Tests")
    print("  0. Exit")
    print("\n" + "="*60)


def main():
    """Main test runner"""
    print("\n✓ WhisperTranscriber Test Suite Started")
    
    while True:
        show_menu()
        choice = input("Select test (0-6): ").strip()
        
        if choice == "0":
            print("\n✓ Exiting test suite")
            break
        elif choice == "1":
            test_basic_transcription()
        elif choice == "2":
            test_language_detection()
        elif choice == "3":
            test_get_text_only()
        elif choice == "4":
            test_with_timestamps()
        elif choice == "5":
            test_different_model_size()
        elif choice == "6":
            test_basic_transcription()
            test_language_detection()
            test_get_text_only()
            test_with_timestamps()
            test_different_model_size()
        else:
            print("✗ Invalid choice")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n✓ Test suite interrupted by user")
        sys.exit(0)
