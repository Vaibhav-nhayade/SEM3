// your code goes here
// Modal logic
const loginBtn = document.getElementById('loginBtn');
const signupBtn = document.getElementById('signupBtn');
const loginModal = document.getElementById('loginModal');
const signupModal = document.getElementById('signupModal');
const closeLogin = document.getElementById('closeLogin');
const closeSignup = document.getElementById('closeSignup');

loginBtn.addEventListener('click', () => {
  loginModal.classList.remove('hidden');
  loginModal.classList.add('flex');
});
signupBtn.addEventListener('click', () => {
  signupModal.classList.remove('hidden');
  signupModal.classList.add('flex');
});
closeLogin.addEventListener('click', () => loginModal.classList.add('hidden'));
closeSignup.addEventListener('click', () => signupModal.classList.add('hidden'));
[loginModal, signupModal].forEach(modal => {
  modal.addEventListener('click', (e) => {
    if (e.target === modal) modal.classList.add('hidden');
  });
});

// Input method switching
const btnPrompt = document.getElementById('btn-prompt');
const btnFile = document.getElementById('btn-file');
const btnDoc = document.getElementById('btn-doc');
const mainInput = document.getElementById('mainInput');

function setActiveInput(btn) {
  [btnPrompt, btnFile, btnDoc].forEach(b => {
    b.classList.remove('bg-blue-600', 'text-white');
    b.classList.add('border', 'border-blue-600', 'text-blue-600', 'bg-white');
  });
  btn.classList.remove('border', 'text-blue-600', 'bg-white');
  btn.classList.add('bg-blue-600', 'text-white');
}

// default: prompt selected
setActiveInput(btnPrompt);

btnPrompt.addEventListener('click', () => {
  setActiveInput(btnPrompt);
  mainInput.placeholder = "Type a meaningful prompt, e.g. 'Create 10 MCQ questions on photosynthesis for 12th grade'";
  mainInput.value = "";
});
btnFile.addEventListener('click', () => {
  setActiveInput(btnFile);
  mainInput.placeholder = "Describe the file's contents or paste text here (this demo doesn't upload files)";
  mainInput.value = "";
});
btnDoc.addEventListener('click', () => {
  setActiveInput(btnDoc);
  mainInput.placeholder = "Paste document text here or type a brief description of the document";
  mainInput.value = "";
});

// Quiz‑type buttons
const quizTypeBtns = document.querySelectorAll('.quiz-type-btn');
quizTypeBtns.forEach(btn => {
  btn.addEventListener('click', () => {
    quizTypeBtns.forEach(b => {
      b.classList.remove('bg-blue-600', 'text-white');
      b.classList.add('text-blue-600', 'border', 'border-blue-600', 'bg-white');
    });
    btn.classList.remove('text-blue-600', 'bg-white');
    btn.classList.add('bg-blue-600', 'text-white');
  });
});

// Generate button placeholder logic
// Generate button - open new page on click
const generateBtn = document.getElementById('generateBtn');
generateBtn.addEventListener('click', () => {
  const input = document.getElementById('mainInput').value.trim();

  if (!input) {
    alert("Please enter a prompt first.");
    return;
  }

  // Example: open a new page (could be your quiz result page)
  // Replace 'quiz.html' with the correct destination
  window.open('quiz.html', '_blank');
});
