import argparse
import os
import json
import jsonlines
import time
import random
import concurrent.futures
from typing import List
from tqdm import tqdm

from utils.register import registry, register_class


@register_class(alias="Scenario.CollaborativeConsultation")
class CollaborativeConsultation:
    def __init__(self, args):
        self.args = args
        self.start_time = time.strftime('%Y-%m-%d %H:%M:%S')

        self.doctors = self._load_doctors(args)
        self.patients = self._load_patients(args.patient_database, args.patient)
        self.reporter = registry.get_class(args.reporter)(args)
        self.host = registry.get_class(args.host)(args)

        self.discussion_mode = args.discussion_mode
        self.max_discussion_turn = args.max_discussion_turn
        self.max_conversation_turn = args.max_conversation_turn
        self.delay_between_tasks = args.delay_between_tasks
        self.max_workers = args.max_workers
        self.save_path = args.save_path
        self.ff_print = args.ff_print

    @staticmethod
    def add_parser_args(parser: argparse.ArgumentParser):
        parser.add_argument("--patient_database", default="patients.json", type=str)
        parser.add_argument("--doctor_database", default="doctor.json", type=str)
        parser.add_argument("--number_of_doctors", default=2, type=int,
                            help="Number of doctors in the consultation collaboration")
        parser.add_argument("--max_discussion_turn", default=4, type=int,
                            help="Max discussion turn between doctors")
        parser.add_argument("--max_conversation_turn", default=10, type=int,
                            help="Max conversation turn between doctor and patient")
        parser.add_argument("--max_workers", default=4, type=int,
                            help="Max workers for parallel diagnosis")
        parser.add_argument("--delay_between_tasks", default=10, type=int,
                            help="Delay between tasks")
        parser.add_argument("--save_path", default="dialog_history.jsonl",
                            help="Save path for dialog history")
        parser.add_argument("--patient", default="Agent.Patient.GPT",
                            help="Registry name of patient agent")
        parser.add_argument("--reporter", default="Agent.Reporter.GPT",
                            help="Registry name of reporter agent")
        parser.add_argument("--host", default="Agent.Host.GPT",
                            help="Registry name of host agent")
        parser.add_argument("--ff_print", default=False, action="store_true",
                            help="Print dialog history")
        parser.add_argument("--parallel", default=False, action="store_true",
                            help="Parallel diagnosis")
        parser.add_argument("--discussion_mode", default="Parallel",
                            choices=["Parallel", "Parallel_with_Critique"],
                            help="Discussion mode")

    def _load_doctors(self, args) -> List:
        """Initialize doctor agents with their diagnosis data."""
        int_to_char = {i: chr(i + 65) for i in range(26)}
        doctors = []

        for i, doctor_args in enumerate(args.doctors_args[:args.number_of_doctors]):
            doctor_cls = registry.get_class(doctor_args.doctor_name)
            doctor = doctor_cls(doctor_args, name=int_to_char[i])
            doctor.load_diagnosis(
                diagnosis_filepath=doctor_args.diagnosis_filepath,
                evaluation_filepath=doctor_args.evaluation_filepath,
                doctor_key=doctor_args.doctor_key
            )
            doctors.append(doctor)
        return doctors

    def _load_patients(self, patient_db_path: str, patient_class: str) -> List:
        """Load patient agents from a JSON database."""
        with open(patient_db_path, "r", encoding="utf-8") as f:
            patient_data = json.load(f)

        patients = []
        patient_cls = registry.get_class(patient_class)
        for entry in patient_data:
            patients.append(patient_cls(
                self.args,
                patient_profile=entry["profile"],
                medical_records=entry["medical_record"],
                patient_id=entry["id"],
            ))
        return patients

    def run(self):
        """Run diagnosis sequentially."""
        self.remove_processed_patients()
        for patient in tqdm(self.patients):
            self._process_patient(patient)

    def parallel_run(self):
        """Run diagnosis in parallel."""
        self.remove_processed_patients()
        start_time = time.time()
        print("Parallel Run Start")

        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = [executor.submit(self._process_patient, patient) for patient in self.patients]
            for _ in tqdm(concurrent.futures.as_completed(futures), total=len(self.patients)):
                pass

        print("Duration: {:.2f}s".format(time.time() - start_time))

    def _process_patient(self, patient):
        """Process a single patient through all consultation stages."""
        symptom_and_examination = self.host.summarize_symptom_and_examination(
            self.doctors, patient, self.reporter
        )
        if self.ff_print:
            print(f"symptom_and_examination: {symptom_and_examination}")

        diagnosis_in_discussion = [self._initial_diagnosis_round(patient, symptom_and_examination)]
        self._discussion_rounds(patient, diagnosis_in_discussion)

        final_diagnosis = self.host.summarize_diagnosis(self.doctors, patient)
        if self.ff_print:
            print(f"host final diagnosis: {final_diagnosis}\n{'='*100}")

        diagnosis_info = {
            "patient_id": patient.id,
            "final_turn": diagnosis_in_discussion[-1]["turn"],
            "diagnosis": final_diagnosis,
            "symptom_and_examination": symptom_and_examination,
            "doctor_database": self.args.doctor_database,
            "doctor_ids": [doc.id for doc in self.doctors],
            "doctor_engine_names": [doc.engine.model_name for doc in self.doctors],
            "host": self.args.host,
            "host_engine_name": self.host.engine.model_name,
            "patient": self.args.patient,
            "patient_engine_name": patient.engine.model_name,
            "reporter": self.args.reporter,
            "reporter_engine_name": self.reporter.engine.model_name,
            "time": self.start_time,
        }
        self.save_info(diagnosis_info)

    def _initial_diagnosis_round(self, patient, symptom_and_examination):
        """First diagnosis pass for all doctors."""
        diagnosis_in_turn = []
        for i, doctor in enumerate(self.doctors):
            doctor.revise_diagnosis_by_symptom_and_examination(patient, symptom_and_examination)
            diagnosis_in_turn.append({
                "doctor_id": i,
                "doctor_engine_name": doctor.engine.model_name,
                "diagnosis": doctor.get_diagnosis_by_patient_id(patient.id)
            })
            if self.ff_print:
                print(doctor.engine.model_name,
                      doctor.get_diagnosis_by_patient_id(patient.id, "诊断结果"))

        host_measurement = self.host.measure_agreement(
            self.doctors, patient, discussion_mode=self.discussion_mode
        )
        return {"turn": 0, "diagnosis_in_turn": diagnosis_in_turn, "host_critique": host_measurement}

    def _discussion_rounds(self, patient, diagnosis_in_discussion):
        """Iterative discussion rounds until agreement or max turns."""
        host_measurement = diagnosis_in_discussion[-1]["host_critique"]
        if host_measurement == '#结束#':
            return

        for turn in range(1, self.max_discussion_turn + 1):
            if self.ff_print:
                print(turn - 1, "host", host_measurement)

            diagnosis_in_turn = []
            for i, doctor in enumerate(self.doctors):
                others = self.doctors[:i] + self.doctors[i + 1:]
                doctor.revise_diagnosis_by_others(
                    patient, others, host_measurement, discussion_mode=self.discussion_mode
                )
                diagnosis_in_turn.append({
                    "doctor_id": i,
                    "doctor_engine_name": doctor.engine.model_name,
                    "diagnosis": doctor.get_diagnosis_by_patient_id(patient.id)
                })
                if self.ff_print:
                    print(turn - 1, i, doctor.name,
                          doctor.get_diagnosis_by_patient_id(patient.id, "诊断结果"))

            host_measurement = self.host.measure_agreement(self.doctors, patient)
            diagnosis_in_discussion.append({
                "turn": turn,
                "diagnosis_in_turn": diagnosis_in_turn,
                "host_critique": host_measurement
            })

            if self.ff_print:
                print(f"host: {host_measurement}\n{'-'*100}")

            if host_measurement == '#结束#':
                break

    def remove_processed_patients(self):
        """Skip patients already processed in save file."""
        processed_ids = set()
        if os.path.exists(self.save_path):
            with jsonlines.open(self.save_path, "r") as f:
                for obj in f:
                    processed_ids.add(obj["patient_id"])

        before_count = len(self.patients)
        self.patients = [p for p in self.patients if p.id not in processed_ids]
        random.shuffle(self.patients)
        print("To-be-diagnosed Patient Number:", len(self.patients),
              f"(removed {before_count - len(self.patients)})")

    def save_info(self, dialog_info):
        """Append diagnosis info to save file."""
        with jsonlines.open(self.save_path, "a") as f:
            f.write(dialog_info)
