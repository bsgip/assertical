from typing import Optional

from sqlalchemy import VARCHAR, ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from assertical.fake.generator import generate_class_instance


class Base(DeclarativeBase):
    pass


class Student(Base):
    """This is to stress test some complex relationships"""

    __tablename__ = "_student"

    student_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # Each student has multiple report cards
    report_cards: Mapped[list["ReportCard"]] = relationship(
        back_populates="student",
        lazy="raise",
        cascade="all, delete",
        passive_deletes=True,
    )


class ReportCard(Base):

    __tablename__ = "_report_card"

    report_card_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("_student.student_id", ondelete="CASCADE"))

    student: Mapped["Student"] = relationship(back_populates="report_cards")

    # Each report card has a unique Math/English result
    math_result: Mapped[Optional["MathResult"]] = relationship(
        back_populates="report_card", uselist=False, lazy="raise"
    )
    english_result: Mapped[Optional["EnglishResult"]] = relationship(
        back_populates="report_card", uselist=False, lazy="raise"
    )


class MathResult(Base):
    __tablename__ = "_math_result"
    math_result_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    report_card_id: Mapped[int] = mapped_column(ForeignKey("_report_card.report_card_id", ondelete="CASCADE"))
    grade: Mapped[str] = mapped_column(VARCHAR(length=32), nullable=False)

    report_card: Mapped["ReportCard"] = relationship(back_populates="math_result", lazy="raise", single_parent=True)


class EnglishResult(Base):
    __tablename__ = "_english_result"
    english_result_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    report_card_id: Mapped[int] = mapped_column(ForeignKey("_report_card.report_card_id", ondelete="CASCADE"))
    grade: Mapped[str] = mapped_column(VARCHAR(length=32), nullable=False)

    report_card: Mapped["ReportCard"] = relationship(back_populates="english_result", lazy="raise", single_parent=True)


def test_generate_complex_relationships():
    """Regression test for picking up a known issue with generate_relationships and more complex types"""

    student = generate_class_instance(Student, generate_relationships=True)
    assert isinstance(student, Student)

    # Student should have generated a report card
    assert isinstance(student.report_cards, list)
    assert len(student.report_cards) == 1

    # Report card should have generated with links to English/Math result
    report_card = student.report_cards[0]
    assert isinstance(report_card.english_result, EnglishResult)
    assert isinstance(report_card.math_result, MathResult)
    assert report_card.student is None or id(report_card.student) == id(
        student
    ), "Back reference will not be populated by our code - SQLAlchemy might auto fill but that's OK"

    english_result = report_card.english_result
    assert english_result.report_card is None or id(english_result.report_card) == id(
        report_card
    ), "Back reference will not be populated by our code - SQLAlchemy might auto fill but that's OK"

    math_result = report_card.math_result
    assert math_result.report_card is None or id(math_result.report_card) == id(
        report_card
    ), "Back reference will not be populated by our code - SQLAlchemy might auto fill but that's OK"

    assert english_result.grade != math_result.grade, "Values should be using unique seeds"
