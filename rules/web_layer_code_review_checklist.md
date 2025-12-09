# Web Layer Code Review Checklist

## 1. Dependency Injection

- [ ] **Use Constructor Injection**: Are all Spring components (`@Controller`, `@Service`, etc.) using constructor injection?
- [ ] **Declare Dependencies as `private final`**: Are dependencies declared as `private final`?
- [ ] **Avoid Field Injection**: Is field injection (`@Autowired` on fields) avoided?

## 2. Controller Layer

- [ ] **Extend a Base Controller**: Does the controller extend a common base class where applicable?
- [ ] **Use Specific Mapping Annotations**: Are `@GetMapping` and `@PostMapping` used instead of `@RequestMapping` for methods?
- [ ] **Define a Base Request Path**: Is `@RequestMapping("/base-path")` used at the class level?
- [ ] **Manage State with `@SessionAttributes`**: Is `@SessionAttributes` used for multi-step forms?
- [ ] **Route Actions with `params`**: Is `params="_action_..."` used to handle different button submissions?
- [ ] **Delegate Logic**: Is the controller thin, with business logic in services and view logic in helpers?
- [ ] **Secure Data Binding with `@InitBinder`**:
    - [ ] Is `binder.setAllowedFields(...)` used to prevent over-posting?
    - [ ] Are different allowed field lists defined for new vs. edit states?
    - [ ] Are custom validators and property editors registered?

## 3. Command Object Pattern

- [ ] **Implement `Serializable`**: Does the command class implement `java.io.Serializable`?
- [ ] **Create a Command per Form**: Is there a dedicated command class for each complex form?
- [ ] **Encapsulate All View Data**: Does the command object hold the primary entity and all auxiliary data for the view?
- [ ] **Name the Command**: Is a `public static final String COMMAND_NAME` defined and used consistently?

## 4. Helper and Validator Pattern

- [ ] **Isolate View Logic in Helpers**: Is view-specific logic placed in dedicated helper classes?
- [ ] **Implement Custom Validation in Validators**: Are custom business rules implemented in a `Validator` class and registered in the `@InitBinder`?

## 5. Finder/Search Framework Review Checklist

- [ ] **Search Command Class**:
    - [ ] Does the class extend `AbstractSearchCmd`?
    - [ ] Is the `@FinderParams` annotation correctly configured?
    - [ ] Is `getAllRoles()` implemented for security?

- [ ] **Field and Column Annotations**:

    - [ ] **`@SearchView`**: Is the annotation present and correctly configured for each search input field?
    - [ ] **`@SearchParam`**: Is the `where` clause correct for each search input field?
    - [ ] **`@OutputColumn`**: Are `columnName` and `messageKey` correct for each results column?

- [ ] **SQL Implementation**:
    - [ ] Are `getSearchSql()` and `getListSql()` implemented?
    - [ ] **Does the SQL string contain the `#WHERE#` placeholder?**

- [ ] **XML Configuration**:
    - [ ] Is a new `<bean>` for the search controller defined in the `*-servlet.xml` file?
    - [ ] Does the bean extend `parentSearchController`?
    - [ ] Is the `commandClass` property set correctly?
    - [ ] Does the `loaderUrl` property point to the correct URL?

## 6. View and Configuration

- [ ] **Use Custom JSP Tags**: Are custom JSP tags from the library used for UI components?
- [ ] **No Java in JSPs**: Is JSTL used for all logic in JSPs, with no Java scriptlets?
- [ ] **Configure Beans in XML**: Are Spring beans defined and configured in `*-servlet.xml` files?
- [ ] **Register Formatters**: Are new formatters for complex types registered in the `conversionService` bean?
