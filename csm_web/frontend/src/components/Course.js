import React from "react";
import { groupBy } from "lodash";
import moment from "moment";
import { post } from "../utils/api";
import { alert_modal } from "../utils/common";

const API_TIME_FORMAT = "HH:mm:ss";
const DISPLAY_TIME_FORMAT = "HH:mm A";
const dayOfWeek = {
  Monday: 0,
  Tuesday: 1,
  Wednesday: 2,
  Thursday: 3,
  Friday: 4,
  Saturday: 5,
  Sunday: 6
};

function CourseDetail(props) {
  return <h1>{props.course}</h1>;
}

class Course extends React.Component {
  constructor(props) {
    super(props);
    this.state = {
      course: {
        name: props.course
      },
      sections: {},
      enrolled: false
    };
  }

  componentDidUpdate(prevProps) {
    if (this.props.course != prevProps.course) {
      this.setState(
        (state, props) => {
          return {
            course: {
              name: props.course
            },
            sections: {},
            enrolled: false
          };
        },
        () => this.updateCourse()
      );
    }
  }

  componentDidMount() {
    this.updateCourse();
  }

  updateCourse() {
    console.log("Beginning update...");
    fetch(`/scheduler/courses/${this.state.course.name}`)
      .then(response => response.json())
      .then(course => {
        this.setState(
          (state, props) => {
            return {
              course: course
            };
          },
          () => {
            // These requests are synchronous on getting course data
            fetch("/scheduler/profiles/")
              .then(response => response.json())
              .then(profiles => {
                this.setState(
                  (state, props) => {
                    const courses = profiles.map(profile => profile.course);
                    return {
                      enrolled: courses.indexOf(state.course.id) != -1
                    };
                  },
                  () => {
                    console.log("Updated Enrolled!");
                    console.log(this.state);
                  }
                );
              });
            fetch(`/scheduler/courses/${this.state.course.name}/sections/`)
              .then(response => response.json())
              .then(sections => {
                this.setState((state, props) => {
                  return {
                    sections: groupBy(
                      sections,
                      section => section.defaultSpacetime.dayOfWeek
                    )
                  };
                });
              });
          }
        );
      });
  }

  render() {
    const days = Object.entries(this.state.sections)
      .sort((item1, item2) => {
        const day1 = dayOfWeek[item1[0]];
        const day2 = dayOfWeek[item2[0]];
        if (day1 == day2) {
          return 0;
        } else if (day1 < day2) {
          return 1;
        } else {
          return -1;
        }
      })
      .reverse()
      .map(item => {
        const [day, sections] = item;
        return (
          <Day
            key={day}
            enrolled={this.state.enrolled}
            day={day}
            sections={sections}
            update={() => this.updateCourse()}
          />
        );
      });

    return (
      <div>
        <div>
          <CourseDetail
            enrolled={this.state.enrolled}
            course={this.state.course.name}
          />
        </div>
        <div>
          <ul uk-accordion="true">{days}</ul>
        </div>
      </div>
    );
  }
}

function Day(props) {
  const sections = props.sections
    .sort((section1, section2) => {
      const time1 = moment(
        section1.defaultSpacetime.startTime,
        API_TIME_FORMAT
      );
      const time2 = moment(
        section2.defaultSpacetime.startTime,
        API_TIME_FORMAT
      );
      return time1 - time2;
    })
    .map((section, index) => {
      return (
        <SectionSummary
          enrolled={props.enrolled}
          section={section}
          key={index}
          update={props.update}
        />
      );
    });
  return (
    <li>
      <a className="uk-accordion-title" href="#">
        {props.day}
      </a>
      <div className="uk-accordion-content">
        <ul>{sections}</ul>
      </div>
    </li>
  );
}

function SectionSummary(props) {
  const spacetime = props.section.defaultSpacetime;
  const startTime = moment(spacetime.startTime, API_TIME_FORMAT).format(
    DISPLAY_TIME_FORMAT
  );
  const location = spacetime.location;

  function handleClick(event) {
    // TODO is there a nicer way to do this with async rather than this external
    // variable?
    var ok = false;
    post(`scheduler/sections/${props.section.id}/enroll`, {})
      .then(response => {
        ok = response.ok;
        return response.json();
      })
      .then(body => {
        if (!ok) {
          if (body.shortCode == "already_enrolled") {
            alert_modal(
              "You are already enrolled in this course. You can only enroll in one section per course.",
              () => {}
            );
          } else if (body.shortCode == "section_full") {
            alert_modal(
              "This section is full. Please try enrolling in another section.",
              () => {}
            );
          } else {
            alert_modal("An unknown error has occurred.", () => {});
            console.log("An unknown error has occurred.");
            console.log(body.message);
          }
        } else {
          alert_modal(
            `You've successfully enrolled in section ${
              props.section.id
            } at ${location}, ${startTime}`,
            () => {}
          );
        }

        // Updates the Course component
        props.update();
      });
  }

  const available = props.section.capacity - props.section.enrolledStudents;
  const pluralized_spot = available == 1 ? "spot" : "spots";

  return (
    <li>
      <h4>
        {location} - {startTime}
      </h4>
      <p>
        {props.section.enrolledStudents}/{props.section.capacity} - {available}{" "}
        {pluralized_spot} available
      </p>
      <button className="uk-button uk-button-default" onClick={handleClick}>
        Enroll
      </button>
    </li>
  );
}

export default Course;
