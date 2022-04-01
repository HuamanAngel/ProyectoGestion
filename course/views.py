from urllib.error import HTTPError
from django.contrib.sites.shortcuts import get_current_site
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden, HttpResponse, JsonResponse
from django.contrib import messages
from django.contrib.auth.models import User
from course.models import Course, Post, Course_User
from course.forms import NewCourseForm, NewPostForm
from django.template.loader import render_to_string
from django.core.mail import send_mail
from django.utils.html import strip_tags

# Create your views here.
@login_required
def index(request):
	user = request.user
	courses = Course.objects.filter(enrolled=user)
	for course in courses:
		print(course.id, course.title)

	context = {
		'courses': courses
	}
	return render(request, 'index.html', context)

def initialize_arrays(courses, u_courses, times):
	for course in courses:
		time = course.time_start
		if time not in times:
			times.append(time)
			u_courses.append([])
	times.sort

def fill_array(u_courses, times):
	for i in range(0, len(times)):
		u_courses[i].sort(key=lambda c: int(c.day))
		j = 0
		while j < 7:
			try:
				if int(u_courses[i][j].day) != (j + 1):
					u_courses[i].insert(j, None)
			except Exception:
				u_courses[i].append(None)
			j += 1
 
@login_required
def new_course(request):
	user = request.user
	if request.method == 'POST':
		form = NewCourseForm(request.POST, request.FILES)
		if form.is_valid():
			time_start = form.cleaned_data.get('time_start')
			time_end = form.cleaned_data.get('time_end')

			if not ValidateTime(request, time_start, time_end):
				context = {'form': form}
				return render(request, 'courses/newcourse.html', context)

			picture = form.cleaned_data.get('picture')
			title = form.cleaned_data.get('title')
			description = form.cleaned_data.get('description')
			syllabus = form.cleaned_data.get('syllabus')
			Course.objects.create(picture=picture, title=title, description=description, 
			time_start=time_start, time_end=time_end,
			syllabus=syllabus, user=user)
			return redirect('../../courses/')
	else:
		form = NewCourseForm()

	context = {
		'form': form,
	}

	return render(request, 'courses/newcourse.html', context)

def ValidateTime(request, time_start, time_end):
	ts = str(time_start).split(":")
	te = str(time_end).split(":")
	confirmation = True

	if ts[1] != "00" or te[1] != "00":
		messages.warning(request, 'La hora de inicio y cierre deben de darse en horas en punto. ' + 
			'Ejm: "Inicio - 8:00 y Fin - 9:00"')
		confirmation = False
	if int(ts[0]) > int(te[0]):
		messages.warning(request, 'La hora de inicio no puede pasar de la hora de cierre.')
		confirmation = False

	return confirmation

@login_required
def show_mycourses(request):
	courses = Course.objects.filter(user=request.user)    

	context = {
		'courses': courses,
	}    
	return render(request, 'courses/mycourses.html', context)

def showCourse(request):
	courses = Course.objects.filter()    
	context = {
		'courses': courses,
	}
	return render(request,'courses/categories.html',context)


@login_required
def NewPost(request, course_id):
	user = request.user
	course = get_object_or_404(Course, id=course_id)

	if user != course.user:
		return HttpResponseForbidden()
	else:
		if request.method == 'POST':
			form = NewPostForm(request.POST, request.FILES)
			if form.is_valid():
				title = form.cleaned_data.get('title')
				content = form.cleaned_data.get('content')
				file = form.cleaned_data.get('file')
				post = Post.objects.create(title=title, content=content, file=file, course_id=course_id)
				course.posts.add(post)
				course.save()
				return redirect('show_posts', course_id=course_id)
		else:
			form = NewPostForm()

	context = {
		'form': form,
	}
	return render(request, 'post/newpost.html', context)

@login_required
def show_posts(request, course_id):
	user = request.user
	course = get_object_or_404(Course, id=course_id)
	posts = Post.objects.filter(course_id=course_id)
	teacher_mode = False
	if user == course.user:
		teacher_mode = True

	context = {
		'teacher_mode': teacher_mode,
		'course': course,
		'posts': posts
	}

	return render(request, 'post/posts.html', context)

@login_required
def show_course_description(request, course_id):
	user = request.user
	course = get_object_or_404(Course, id=course_id)
	is_registered = Course_User.objects.filter(course=course_id, user=user.id).all()
	is_owner = (user == course.user)
	
	print(is_owner)

	context = {
		'course': course,
		'user': user,
		'is_registered': is_registered,
		'is_owner': is_owner
	}

	return render(request, 'courses/course.html', context)

@login_required
def sendInscriptionLink(request, course_id):
	if request.method == 'POST':
		to_email = request.POST.get('to_email')
		if to_email:
			user_owner =  request.user
			current_site = get_current_site(request)
			from_email = user_owner.email
			course = Course.objects.get(id=course_id)
			
			subject = 'Correo de prueba'
			html_message = render_to_string("courses/email_invitation.html", {
				"domain": current_site.domain,
				"user": user_owner,
				"course": course,
				"codeInvitation": str(course.codeinvitation)
			},)
			plain_message = strip_tags(html_message)
			send_mail(subject, plain_message, from_email , [to_email], html_message=html_message)

			return HttpResponse('Correo enviado a ' + to_email)
		else:
			return HTTPError('Email vacio')

@login_required
def usersInCourse(request, course_id):
	users_query = Course_User.objects.filter(course=course_id).all()
	data = []
	for user in users_query:
		user_dict = {
			"name": str(user.user),
			"email": str(user.user.email),
			"picture": str(user.user.profile.picture)
		}
		data.append(user_dict)
	return JsonResponse({'users': data})

@login_required
def inscriptionLink(request, codeInvitation):
	try:
		course = Course.objects.get(codeinvitation=codeInvitation)
		already_inscription = Course_User.objects.filter(user=request.user.id, course=course.id)     
		if already_inscription:
			messages.error(request, 'Ya estas inscrito en este curso')
			return redirect('/user/inscription/')
		else:  
			Course_User.objects.create(user=request.user, course=course)
			messages.success(request, 'Inscripcion correcta')
			return redirect('/user/inscription/')
	except:
		return HttpResponse('Link de activación inválido')
	