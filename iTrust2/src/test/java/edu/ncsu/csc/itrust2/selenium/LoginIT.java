package edu.ncsu.csc.itrust2.selenium;

import edu.ncsu.csc.itrust2.cucumber.SeleniumTest;

public class LoginIT extends SeleniumTest {

    // private final String baseUrl = "http://localhost:8080/iTrust2";
    // private static final String HOME_URL =
    // "http://localhost:8080/iTrust2/ROLE/index";
    //
    // @Before
    // public void init () {
    // super.setup();
    // }
    //
    // @After
    // public void teardown () {
    // super.tearDown();
    // }
    //
    // private void testLogin ( final String role ) {
    // driver.get( baseUrl );
    // final WebElement username = driver.findElement( By.name( "username" ) );
    // username.clear();
    // username.sendKeys( role );
    // final WebElement password = driver.findElement( By.name( "password" ) );
    // password.clear();
    // password.sendKeys( "123456" );
    // final WebElement submit = driver.findElement( By.className( "btn" ) );
    // submit.click();
    // assertEquals( HOME_URL.replace( "ROLE", role ), driver.getCurrentUrl() );
    // }
    //
    // @Test
    // public void hcpShouldLogIn () {
    // testLogin( "hcp" );
    // }
    //
    // @Test
    // public void patientShouldLogIn () {
    // testLogin( "patient" );
    // }
    //
    // @Test
    // public void adminShouldLogIn () {
    // testLogin( "admin" );
    // }
}
