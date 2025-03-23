function checkLogin() {
    const username = document.getElementById("username").value;
    const password = document.getElementById("password").value;

    // Проверка логина для админа
    if (username === "admin" && password === "1234") {
        localStorage.setItem("loggedIn", "true");
        localStorage.setItem("role", "admin");  // Сохраняем роль пользователя
        showContent();
    } else {
        // Проверка на HR-специалиста
        let users = JSON.parse(localStorage.getItem("users")) || [];
        let user = users.find(user => user.username === username && user.password === password);
        
        if (user) {
            localStorage.setItem("loggedIn", "true");
            localStorage.setItem("role", user.position);  // Сохраняем должность HR-специалиста
            showContent();
        } else {
            alert("Неверный логин или пароль");
        }
    }
}

// Функция для отображения контента после входа
function showContent() {
    // Скрыть форму входа и регистрации
    document.getElementById("login-form").style.display = "none";
    document.getElementById("register-form-container").style.display = "none";
    document.getElementById("header").classList.remove("hidden"); // Показываем верхнюю панель
    document.getElementById("content").style.display = "block"; // Показываем основной контент
    updateEmployeeList(); // Обновляем список сотрудников
}

// Функция для выхода из аккаунта
function logout() {
    localStorage.removeItem("loggedIn");
    localStorage.removeItem("role");
    document.getElementById("header").classList.add("hidden"); // Скрыть верхнюю панель
    document.getElementById("content").style.display = "none"; // Скрыть основной контент
    document.getElementById("login-form").style.display = "block"; // Показать форму входа
    document.getElementById("register-form-container").style.display = "block"; // Показать форму регистрации
}

// Функция для регистрации пользователя
function registerUser() {
    const firstName = document.getElementById("first-name").value;
    const lastName = document.getElementById("last-name").value;
    const position = document.getElementById("position").value;
    const password = document.getElementById("password-register").value;

    // Проверка, что все поля заполнены
    if (firstName && lastName && position && password) {
        const username = `${firstName} ${lastName}`; // Логин - это имя + фамилия
        const newUser = { username, position, password }; // Новый пользователь

        // Получаем список пользователей из localStorage
        let users = JSON.parse(localStorage.getItem("users")) || [];

        // Проверка на дублирование логина
        const existingUser = users.find(user => user.username === username);
        if (existingUser) {
            alert("Пользователь с таким логином уже существует!");
            return;
        }

        // Добавляем нового пользователя в список
        users.push(newUser);
        localStorage.setItem("users", JSON.stringify(users)); // Сохраняем обновленный список

        alert("Пользователь успешно зарегистрирован");
        // Скрываем форму регистрации
        document.getElementById("register-form-container").style.display = "none"; 
    } else {
        alert("Заполните все поля!");
    }
}
// Функция для удаления пользователя (доступна только администратору)
function deleteUser(username) {
    if (localStorage.getItem("role") === "admin") {
        let users = JSON.parse(localStorage.getItem("users")) || [];
        users = users.filter(user => user.username !== username); // Удаляем пользователя по имени
        localStorage.setItem("users", JSON.stringify(users));

        // Обновить список сотрудников
        updateEmployeeList();
        alert("Пользователь успешно удален");
    } else {
        alert("У вас нет прав для удаления пользователей");
    }
}

// Функция для обновления списка сотрудников
function updateEmployeeList() {
    const employeeList = document.getElementById("employee-list");
    let users = JSON.parse(localStorage.getItem("users")) || [];
    
    // Очистить текущий список
    employeeList.innerHTML = "";

    // Добавить пользователей в список
    users.forEach(user => {
        const listItem = document.createElement("li");
        listItem.classList.add("employee-item");
        listItem.innerHTML = `${user.username} - ${user.position} - <a href="report-${user.username}.html" target="_blank">Отчеты</a>`;
        
        // Добавить кнопку удаления, если пользователь админ
        if (localStorage.getItem("role") === "admin") {
            const deleteButton = document.createElement("button");
            deleteButton.textContent = "Удалить";
            deleteButton.classList.add("delete-btn");
            deleteButton.onclick = function() {
                deleteUser(user.username);
            };
            listItem.appendChild(deleteButton);
        }

        employeeList.appendChild(listItem);
    });
}

// Проверка статуса входа при загрузке страницы
window.onload = function() {
    if (localStorage.getItem("loggedIn") === "true") {
        showContent();
    } else {
        document.getElementById("header").classList.add("hidden"); // Скрыть верхнюю панель
    }
}