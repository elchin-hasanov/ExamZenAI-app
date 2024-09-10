from django.contrib.auth import authenticate, login
from django.contrib import messages
from .forms import SignUpForm, LoginForm
from .forms import *
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout
from main.models import *
from django.db.models import Sum
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Question, Subject
import random
from .models import User, Reward, Test
import json
import re
import openai
from django.contrib.staticfiles import finders
from django.shortcuts import render
from django.http import JsonResponse
from difflib import SequenceMatcher
import openai
import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import Highlight

# Configure your OpenAI API key
admin_user = User.objects.get(username='apikey')
latest_test = Test.objects.filter(user=admin_user).order_by('-created_at').first()
openai.api_key = latest_test.answers


def home(request):
    return render(request, 'main/home.html')

def login_view(request):
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                return redirect('main:zens')
            else:
                messages.error(request, 'Invalid username or password.')
                print("Invalid login attempt")
        else:
            print("Form is not valid")
    else:
        form = LoginForm()
    return render(request, 'main/login.html', {'form': form})

def signup_view(request):
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            user = authenticate(username=form.cleaned_data['username'], password=form.cleaned_data['password1'])
            login(request, user)
            return redirect('main:zens')
        else:
            print("Form is not valid")
    else:
        form = SignUpForm()
    return render(request, 'main/signup.html', {'form': form})

@login_required
def logout_view(request):
    logout(request)
    return redirect('main:home')

def zen(request):
    return render(request, 'main/zens.html')

def lobby(request):
    subject = request.GET.get('subject', '')
    return render(request, 'main/lobby.html', {'subject': subject})

# @login_required
def questionbank(request):
    subject_name = request.GET.get('subject_name', '')
    if subject_name:
        subject = get_object_or_404(Subject, name=subject_name)
        questions = Question.objects.filter(subject=subject)
    else:
        questions = Question.objects.all()  # Handle if no subject_name provided
    return render(request, 'main/questionbank.html', {'questions': questions, 'subject_name': subject_name})

# @login_required
def question_answer(request, question_id):
    question = get_object_or_404(Question, id=question_id)
    choices = question.choices.split('\\n') if question.choices else []
    return render(request, 'main/question_answer.html', {'question': question, 'choices': choices})

@login_required
def test(request):
    subject_name = request.GET.get('subject', '')
    paper = request.GET.get('paper', '1')
    context = {}

    if subject_name:
        subject = get_object_or_404(Subject, name=subject_name)
        
        if subject_name in ["Math", "Physics", "Chemistry"]:
            if paper == '1':
                questions_paper1 = list(Question.objects.filter(subject=subject, paper='1'))
                selected_questions_paper1 = random.sample(questions_paper1, min(11 if subject_name == "Math" else 40, len(questions_paper1)))
                test_instance_paper1 = Test.objects.create(user=request.user, subject=subject, paper='1')
                for question in selected_questions_paper1:
                    test_instance_paper1.questions.add(question)
                
                questions_paper2 = list(Question.objects.filter(subject=subject, paper='2'))
                selected_questions_paper2 = random.sample(questions_paper2, min(6, len(questions_paper2)))
                test_instance_paper2 = Test.objects.create(user=request.user, subject=subject, paper='2')
                for question in selected_questions_paper2:
                    test_instance_paper2.questions.add(question)
                
                context = {
                    'subject': subject,
                    'questions_paper1': selected_questions_paper1,
                    'questions_paper2': selected_questions_paper2,
                    'paper': '1',
                    'test_instance_paper1': test_instance_paper1,
                    'test_instance_paper2': test_instance_paper2,
                }

        elif subject_name == "History":
            questions = list(Question.objects.filter(subject=subject))
            questions_by_topic = {}
            for question in questions:
                topic = question.topic
                if topic not in questions_by_topic:
                    questions_by_topic[topic] = []
                questions_by_topic[topic].append(question)
            selected_questions_by_topic = {topic: random.sample(questions, min(2, len(questions))) for topic, questions in questions_by_topic.items()}
            test_instance_paper2 = Test.objects.create(user=request.user, subject=subject, paper='2')
            for question in questions:
                test_instance_paper2.questions.add(question)
            context = {'subject': subject, 'questions_by_topic': selected_questions_by_topic}

        elif subject_name == "English":
            questions = list(Question.objects.filter(subject=subject))
            selected_questions = random.sample(questions, min(4, len(questions)))
            test_instance_paper2 = Test.objects.create(user=request.user, subject=subject, paper='2')
            for question in selected_questions:
                test_instance_paper2.questions.add(question)
            context = {'subject': subject, 'questions': selected_questions}

        if context:  # Check if context is not empty
            for key in ['questions_paper1', 'questions_paper2', 'questions']:
                if key in context:
                    for question in context[key]:
                        question.choices_list = question.choices.split('\\n') if question.choices else []
            return render(request, 'main/test.html', context)

    return redirect('main:zens')  # Default redirect if subject_name is missing or no valid context

@login_required
def submit_exam(request):
    if request.method == 'POST':
        paper1_instance = Test.objects.filter(user=request.user, paper='1').order_by('-created_at').first()
        paper2_instance = Test.objects.filter(user=request.user, paper='2').order_by('-created_at').first()

        if paper1_instance:
            paper1_answers = request.POST.get('answers_paper1', '')
            paper1_instance.answers = paper1_answers
            paper1_instance.save()

            # Count correct Paper 1 answers
            correct_answers_count = 0
            for question in paper1_instance.questions.all():
                user_answer = request.POST.get(f'answers_{question.id}')
                if user_answer == question.answer:
                    correct_answers_count += 1
            paper1_instance.paper1_correct_answers = correct_answers_count

            paper1_instance.save()

        if paper2_instance:
            paper2_answers = request.POST.get('answers_paper2', '')
            paper2_instance.answers = paper2_answers
            paper2_instance.save()

        context = {
            'paper1_instance': paper1_instance,
            'paper2_instance': paper2_instance,
        }

        return render(request, 'main/submit_exam.html', context)

    return redirect('main:zens')

@login_required
def profile(request):
    user = request.user
    recent_tests = Test.objects.filter(user=user).order_by('-created_at')[:5]
    total_points = Reward.objects.filter(user=user).aggregate(Sum('points'))['points__sum'] or 0
    total_tests = Test.objects.filter(user=user, paper=1, subject__name="Physics").count()
    if total_tests == 0:
        average_score = total_points / 1
    else:
        average_score = total_points / total_tests
    

    context = {
        'username': user.username,
        'total_points': total_points,
        'total_tests': total_tests,
        'average_score': average_score,
        'recent_tests': recent_tests,
    }
    
    return render(request, 'main/profile.html', context)

@login_required
def feedback(request):
    selected_question_id = request.POST.get('selected_question_id', '')
    submitted_answer = request.POST.get('answer', '')
    selected_question = Question.objects.get(id=selected_question_id) if selected_question_id else None

    admin_user = User.objects.get(username='apikey')
    latest_test = Test.objects.filter(user=admin_user).order_by('-created_at').first()

    openai.api_key = latest_test.answers
    criteria_path = finders.find('samples/criteria.json')

    # Load the criteria
    with open(criteria_path, 'r') as f:
        criteria = json.load(f)

    # Load the teacher's tips and criteria for assessing Paper 2 exams
    teacher_tips = """
    Under Criterion A, I will be expecting how much knowledge you have about the texts you studied in relation to the question.
    Under Criterion B, I will be expecting you to use literary features and quotes that compare and contrast the texts and how they connect to the chosen question.
    Under Criterion C, I will be looking for how balanced your answer is with reference to the question, and whether you are focused or deviating from the main idea.
    Under Criterion D, I will be expecting you to use academic language to write your answer.
    """

    # Sample comments are loaded as well
    sample_comments = """
    [Example Sample Comments]
    Criterion A: "A good understanding of both texts in terms of the question with a nuanced thesis. However, references and examples were not always very precise."
    Criterion B: "There is adequate analysis of the novels generally but there is no mention of the similarities and differences in terms of author choices. There is a superficial analysis."
    Criterion C: "Good attention to the question and a clear thesis. Clear paragraphing. More balance between two texts needed."
    Criterion D: "Excellent language and clear writing. Eloquent and well-written."
    """
    
    def replace_bold(text):
        text1 = text.replace('#', '')
        text2 = text1.replace('{}', '')
        return re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', text2)
    
    # Function to assess the essay
    def assess_essay(essay_text, question_text, criteria):
        criteria_context = "\n".join([
            f"Criterion A (Knowledge, understanding and interpretation): {criteria['Criterion A']['title']}",
            f"Levels: {json.dumps(criteria['Criterion A']['levels'], indent=2)}",
            f"Criterion B (Analysis and evaluation): {criteria['Criterion B']['title']}",
            f"Levels: {json.dumps(criteria['Criterion B']['levels'], indent=2)}",
            f"Criterion C (Focus and organization): {criteria['Criterion C']['title']}",
            f"Levels: {json.dumps(criteria['Criterion C']['levels'], indent=2)}",
            f"Criterion D (Language): {criteria['Criterion D']['title']}",
            f"Levels: {json.dumps(criteria['Criterion D']['levels'], indent=2)}"
        ])
        prompt = f"""
        Essay:\n{essay_text}\n\nQuestion:\n{question_text}\n\nCriteria:\n{criteria_context}\n\n
        Based on the criteria, tips, and the samples provided, analyze the essay and provide scores for each criterion with a detailed commentary on each criterion. Check the samples, and relative to the word count, build a ratio for the criterion a and b markings. According to the word count in the test essay given, I want you to give out the criterion a and b marks according to this ratio, and make the criterion a and criterion b markings strict. 
        {teacher_tips}
        {sample_comments}
        """

        response = openai.ChatCompletion.create(
            model="gpt-4-turbo",
            messages=[
                {"role": "system", "content": "You are an essay grader. You will assess the essay based on the provided criteria, tips, sample comments, and the given question. Provide scores for each criterion along with detailed commentary."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=2000,
            temperature=0.5,
        )
        response_content = response['choices'][0]['message']['content']

        # Extract and adjust the marks from the response
        marks_dict = {}
        try:
            for line in response_content.split('\n'):
                if line.startswith("Criterion A"):
                    marks_dict['criterion_a'] = int(re.findall(r'\d+', line)[0])
                elif line.startswith("Criterion B"):
                    marks_dict['criterion_b'] = int(re.findall(r'\d+', line)[0])
                elif line.startswith("Criterion C"):
                    marks_dict['criterion_c'] = max(0, int(re.findall(r'\d+', line)[0]))
                elif line.startswith("Criterion D"):
                    marks_dict['criterion_d'] = max(0, int(re.findall(r'\d+', line)[0]))
        except IndexError:
            print("Failed to extract marks from the response.")
            return response_content

        # Generate final assessment
        assessment = f"Marks:\n{json.dumps(marks_dict, indent=2)}\n\n"
        response_content_without_marks = re.sub(r'Criterion A.*\nCriterion B.*\n', '', response_content, flags=re.DOTALL)
        assessment += response_content_without_marks
        return assessment

    assessment = assess_essay(submitted_answer, selected_question, criteria)
    bold_assessment = replace_bold(assessment)

    return render(request, "main/feedback.html", {
        'submitted_answer': submitted_answer,
        'selected_question': selected_question,
        "comments" : bold_assessment
    })

def tools(request):
    return render(request, "main/tools.html")

@csrf_exempt
def save_highlight(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        highlighted_text = data.get('text')
        literary_device = data.get('literary_device')
        session_id = data.get('session')

        highlight = Highlight(
            user=request.user,
            highlighted_text=highlighted_text,
            literary_device=literary_device,
            session=session_id
        )
        highlight.save()

        return JsonResponse({'status': 'success'})
    return JsonResponse({'status': 'error'}, status=400)

def lit_devices(request):
    literaryDevices = {
            "Alliteration": "The repetition of the same initial consonant sounds in a sequence of words.",
            "Foreshadowing": "A literary device used to give an indication or hint of what is to come later in the story.",
            "Allegory": "A narrative that uses symbolic figures, actions, or events to convey a message or teach a lesson.",
            "Motif": "A recurring element, theme, or idea in a literary work that has symbolic significance.",
            "Simile": "A figure of speech that makes a comparison between two unlike things using 'like' or 'as'.",
            "Colloquialism": "The use of informal language and slang in writing.",
            "Anachronism": "A chronological inconsistency where something is placed outside of its proper time period.",
            "Diction": "The choice and use of words and phrases in speech or writing.",
            "Imagery": "Visually descriptive or figurative language used to create pictures in the reader's mind.",
            "Personification": "Attributing human characteristics to non-human things or abstract ideas.",
            "Euphemism": "A mild or indirect word or expression substituted for one considered too harsh or blunt.",
            "Analogy": "A comparison between two things, typically for the purpose of explanation or clarification.",
            "Hyperbole": "An exaggerated statement or claim not meant to be taken literally.",
            "Antithesis": "A rhetorical device in which two opposite ideas are put together in a sentence for a contrasting effect.",
            "Epigraph": "A short quotation or saying at the beginning of a book or chapter, intended to suggest its theme.",
            "Juxtaposition": "The fact of two things being seen or placed close together with contrasting effect.",
            "Onomatopoeia": "A word that phonetically imitates, resembles, or suggests the sound it describes.",
            "Allusion": "An indirect or passing reference to an event, person, place, or artistic work.",
            "Metaphor": "A figure of speech that describes an object or action in a way that isn’t literally true, but helps explain an idea.",
            "Anthropomorphism": "The attribution of human characteristics or behavior to a god, animal, or object.",
            "Irony": "A contrast or incongruity between expectations for a situation and what is reality.",
            "Anaphora": "The repetition of a word or phrase at the beginning of successive clauses.",
            "Oxymoron": "A figure of speech in which contradictory terms appear in conjunction.",
            "Flashback": "A scene set in a time earlier than the main story.",
            "Litotes": "A figure of speech that employs understatement by using double negatives or a positive statement expressed by negating its opposite.",
            "Chiasmus": "A rhetorical or literary figure in which words, grammatical constructions, or concepts are repeated in reverse order.",
            "Antanaclasis": "A rhetorical device in which a word or phrase is repeatedly used, but the meaning of the word changes in each case.",
            "Rhetorical Question": "A question asked for effect or to make a point rather than to get an answer.",
            "Asyndeton": "The omission or absence of a conjunction between parts of a sentence.",
            "Parallelism": "The use of successive verbal constructions in poetry or prose that correspond in grammatical structure.",
            "Apostrophe": "A figure of speech in which the speaker addresses someone absent, dead, or an inanimate object as if it were present and capable of responding.",
            "Epiphora": "The repetition of a word or phrase at the end of successive clauses or sentences.",
            "Anadiplosis": "A form of repetition in which the last word of one clause or sentence is repeated as the first word of the following clause or sentence.",
            "Assonance": "The repetition of vowel sounds in nearby words.",
            "Climax": "The most intense, exciting, or important point of a story; a culmination or apex.",
            "Metonymy": "The substitution of the name of an attribute or adjunct for that of the thing meant.",
            "Synecdoche": "A figure of speech in which a part is made to represent the whole or vice versa.",
            "Polysyndeton": "The use of several conjunctions in close succession, especially where some could otherwise be omitted.",
            "Zeugma": "A figure of speech in which a word applies to multiple parts of the sentence.",
            "Ellipsis": "The omission from speech or writing of a word or words that are superfluous or able to be understood from contextual clues.",
            "Epanalepsis": "A figure of speech in which the beginning of a clause or sentence is repeated at the end of that same clause or sentence.",
            "Negative Space": "A visual device where the space around and between the subject(s) of an image is used to create another image or enhance the composition.",
            "Gutter": "The space between panels in comics and graphic novels; often used to control pacing and narrative flow.",
            "In Media Res": "A narrative that begins in the middle of the action.",
            "Frame Narrative": "A story within a story, whereby the main narrative is presented at least in part, as an embedded story.",
            "Circular Narrative": "A narrative device in which the story's conclusion returns to its starting point.",
            "Anastrophe": "A form of literary device wherein the order of the noun and the adjective in the sentence is exchanged.",
            "Aporia": "An expression of doubt or uncertainty by a speaker who seems unsure of how to proceed."
        }
    
    
    return render(request, 'main/lit_devices.html')

def generate_paragraph_with_literary_devices():
    # Generate a paragraph with literary devices
        response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are a creative writer."},
            {"role": "user", "content": "Write a 25-50 line paragraph with various literary devices. Do not label the devices."}
        ],
        max_tokens=500,
        temperature=0.7
    )
    
        paragraph = response['choices'][0]['message']['content'].strip()
        return paragraph

def check_literary_devices(paragraph, device_dict):
    # Step 1: Analyze all literary devices comprehensively
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are a literary analyst. Your task is to identify all literary devices in a given paragraph and evaluate the user's identification of these devices."},
            {"role": "user", "content": f"Analyze the following paragraph and comprehensively identify all the literary devices present. Provide the analysis in the format: 'Sentence: \"...\", device_name: \"...\"'. Note that some phrases may contain multiple literary devices.\n\nParagraph:\n{paragraph}"}
        ],
        max_tokens=300,
        temperature=0.3
    )

    # Get the comprehensive analysis from the AI
    comprehensive_analysis = response['choices'][0]['message']['content'].strip()

    # Step 2: Check user's entry against the comprehensive analysis
    user_input_feedback = "Evaluate the user's highlighted literary devices. For each entry, indicate whether it is correct or incorrect based on the comprehensive analysis provided. If the user has missed any devices, list them separately with brief explanations for each missed device."

    # Prepare the formatted user input for clarity
    formatted_user_input = "\n".join([f'User input: "{phrase}" - {device}' for phrase, device in device_dict.items()])

    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are a literary analyst."},
            {"role": "user", "content": f"{user_input_feedback}\n\nParagraph:\n{paragraph}\n\nComprehensive Analysis:\n{comprehensive_analysis}\n\n{formatted_user_input}"}
        ],
        max_tokens=350,
        temperature=0.3
    )

    # Get the result of the user's dictionary check
    result = response['choices'][0]['message']['content'].strip()
    
    return result

from django.shortcuts import render
from .models import Highlight


def lit_search(request):
    if 'submit' in request.GET:
        # User has submitted, process the highlights and show the result
        text = request.GET.get('text')  # Retrieve the generated text that was passed in the form

        latest_highlight = Highlight.objects.filter(user=request.user).order_by('-id').first()
        latest_session = latest_highlight.session if latest_highlight else None

        highlights_dict = {}  # Fetch the user's highlights from the database or session (placeholder)
        
        highlights = Highlight.objects.filter(user=request.user).order_by('id')

        for highlight in highlights:
        # Only store highlights from previous sessions, ignore the current one
            if highlight.session == latest_session:
               highlights_dict[highlight.highlighted_text] = highlight.literary_device
            else:
               break


        # Evaluate user's highlights against the correct literary devices (function to be implemented)
        result = check_literary_devices(text, highlights_dict)  # Compare highlights with correct ones

        # Render the same template with the result
        return render(request, 'main/lit_search.html', {'text': text, 'result': result})

    # Initial page load (generates the text)
    text = generate_paragraph_with_literary_devices()

    # No result yet, since the user hasn't submitted
    return render(request, 'main/lit_search.html', {'text': text, 'result': None})

